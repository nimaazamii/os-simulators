"""Page-replacement algorithms (FIFO, LRU, OPT, Clock) and a TLB model."""
from __future__ import annotations

from collections import OrderedDict, deque
from dataclasses import dataclass


@dataclass
class PagingResult:
    faults: int
    hits: int
    fault_flags: list[bool]
    frames_history: list[list[int]]

    @property
    def fault_rate(self) -> float:
        total = self.faults + self.hits
        return self.faults / total if total else 0.0


def _check(refs: list[int], frames: int) -> None:
    if frames < 1:
        raise ValueError("frames must be >= 1")
    if any(r < 0 for r in refs):
        raise ValueError("page numbers must be non-negative")


def _result(flags: list[bool], hist: list[list[int]]) -> PagingResult:
    f = sum(flags)
    return PagingResult(f, len(flags) - f, flags, hist)


def fifo(refs: list[int], frames: int) -> PagingResult:
    _check(refs, frames)
    mem: deque[int] = deque()
    flags, hist = [], []
    for p in refs:
        fault = p not in mem
        if fault:
            if len(mem) == frames:
                mem.popleft()
            mem.append(p)
        flags.append(fault); hist.append(list(mem))
    return _result(flags, hist)


def lru(refs: list[int], frames: int) -> PagingResult:
    _check(refs, frames)
    mem: OrderedDict[int, None] = OrderedDict()
    flags, hist = [], []
    for p in refs:
        fault = p not in mem
        if fault:
            if len(mem) == frames:
                mem.popitem(last=False)
            mem[p] = None
        else:
            mem.move_to_end(p)
        flags.append(fault); hist.append(list(mem))
    return _result(flags, hist)


def optimal(refs: list[int], frames: int) -> PagingResult:
    """Belady's optimal policy: evict the page whose next use is farthest in the future (needs the whole trace)."""
    _check(refs, frames)
    mem: list[int] = []
    flags, hist = [], []
    for i, p in enumerate(refs):
        fault = p not in mem
        if fault:
            if len(mem) == frames:
                def next_use(q: int) -> float:
                    try:
                        return refs.index(q, i + 1)
                    except ValueError:
                        return float("inf")
                mem.remove(max(mem, key=next_use))
            mem.append(p)
        flags.append(fault); hist.append(list(mem))
    return _result(flags, hist)


def clock(refs: list[int], frames: int) -> PagingResult:
    """Second-chance (clock) replacement with a reference bit per frame."""
    _check(refs, frames)
    slots: list[int | None] = [None] * frames
    ref_bit = [False] * frames
    hand = 0
    flags, hist = [], []
    for p in refs:
        if p in slots:
            ref_bit[slots.index(p)] = True
            flags.append(False)
        else:
            while slots[hand] is not None and ref_bit[hand]:
                ref_bit[hand] = False
                hand = (hand + 1) % frames
            slots[hand], ref_bit[hand] = p, True
            hand = (hand + 1) % frames
            flags.append(True)
        hist.append([s for s in slots if s is not None])
    return _result(flags, hist)


class TLB:
    """Fully associative LRU translation look-aside buffer."""

    def __init__(self, entries: int) -> None:
        if entries < 1:
            raise ValueError("entries must be >= 1")
        self.entries, self._map = entries, OrderedDict()
        self.hits = self.misses = 0

    def lookup(self, page: int, frame_of) -> int:
        """Translate ``page`` using ``frame_of(page)`` on a miss; returns the frame number."""
        if page in self._map:
            self._map.move_to_end(page)
            self.hits += 1
            return self._map[page]
        self.misses += 1
        frame = frame_of(page)
        if len(self._map) == self.entries:
            self._map.popitem(last=False)
        self._map[page] = frame
        return frame

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total else 0.0


def effective_access_time(hit_rate: float, tlb_ns: float, memory_ns: float) -> float:
    """EAT with a single-level page table: hit = tlb + mem; miss = tlb + 2 * mem."""
    if not 0.0 <= hit_rate <= 1.0:
        raise ValueError("hit_rate must be in [0, 1]")
    return hit_rate * (tlb_ns + memory_ns) + (1 - hit_rate) * (tlb_ns + 2 * memory_ns)
