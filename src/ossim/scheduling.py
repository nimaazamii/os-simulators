"""CPU scheduling simulator: FCFS, SJF, SRTF, Round Robin and (non-)preemptive priority scheduling."""
from __future__ import annotations

from dataclasses import dataclass
from statistics import mean


@dataclass(frozen=True)
class Process:
    pid: str
    arrival: int
    burst: int
    priority: int = 0          # smaller number = higher priority


@dataclass
class ProcessResult:
    pid: str
    arrival: int
    burst: int
    start: int                 # first time on the CPU
    completion: int

    @property
    def turnaround(self) -> int:
        return self.completion - self.arrival

    @property
    def waiting(self) -> int:
        return self.turnaround - self.burst

    @property
    def response(self) -> int:
        return self.start - self.arrival


@dataclass
class Schedule:
    gantt: list[tuple[str, int, int]]            # (pid or 'idle', start, end), adjacent equal pids merged
    results: dict[str, ProcessResult]
    context_switches: int

    @property
    def makespan(self) -> int:
        return self.gantt[-1][2] if self.gantt else 0

    @property
    def cpu_utilization(self) -> float:
        busy = sum(e - s for pid, s, e in self.gantt if pid != "idle")
        return busy / self.makespan if self.makespan else 0.0

    def averages(self) -> dict[str, float]:
        r = list(self.results.values())
        return {"waiting": mean(x.waiting for x in r), "turnaround": mean(x.turnaround for x in r),
                "response": mean(x.response for x in r)}


def _validate(procs: list[Process]) -> None:
    if not procs:
        raise ValueError("no processes")
    if len({p.pid for p in procs}) != len(procs):
        raise ValueError("duplicate pid")
    for p in procs:
        if p.burst <= 0 or p.arrival < 0:
            raise ValueError(f"invalid process {p.pid}: burst must be > 0 and arrival >= 0")


def _simulate(procs: list[Process], pick, quantum: int | None = None, preemptive_key: bool = False) -> Schedule:
    """Unit-step simulation. ``pick(ready, remaining, now)`` returns the pid to run; the running process is
    re-evaluated every time unit when ``preemptive_key`` is True, otherwise it keeps the CPU until it finishes
    (or, with a quantum, until the quantum expires)."""
    _validate(procs)
    by_id = {p.pid: p for p in procs}
    remaining = {p.pid: p.burst for p in procs}
    start: dict[str, int] = {}
    completion: dict[str, int] = {}
    queue: list[str] = []                       # ready queue in arrival order (used by RR / FCFS tie-breaks)
    arrived: set[str] = set()
    gantt: list[tuple[str, int, int]] = []
    now, running, run_since, switches, last = 0, None, 0, 0, None

    def admit(t: int) -> None:
        for p in sorted(procs, key=lambda q: (q.arrival, q.pid)):
            if p.arrival <= t and p.pid not in arrived:
                arrived.add(p.pid); queue.append(p.pid)

    admit(0)
    while len(completion) < len(procs):
        if running is None:
            if not queue:
                nxt = min(p.arrival for p in procs if p.pid not in arrived)
                gantt.append(("idle", now, nxt)); now = nxt; admit(now); last = None
                continue
            running = pick(queue, remaining, now)
            queue.remove(running); run_since = 0
            if last is not None and last != running:
                switches += 1
            start.setdefault(running, now)
        gantt.append((running, now, now + 1))
        now += 1; run_since += 1; remaining[running] -= 1
        admit(now)
        last = running
        if remaining[running] == 0:
            completion[running] = now; running = None
        elif quantum is not None and run_since >= quantum:
            queue.append(running); running = None
        elif preemptive_key:
            queue.append(running); running = None   # re-evaluate through pick (the same pid may be picked again)
    merged: list[tuple[str, int, int]] = []
    for pid, s, e in gantt:
        if merged and merged[-1][0] == pid and merged[-1][2] == s:
            merged[-1] = (pid, merged[-1][1], e)
        else:
            merged.append((pid, s, e))
    results = {pid: ProcessResult(pid, by_id[pid].arrival, by_id[pid].burst, start[pid], completion[pid]) for pid in by_id}
    return Schedule(merged, results, switches)


def fcfs(procs: list[Process]) -> Schedule:
    return _simulate(procs, lambda q, rem, now: q[0])


def sjf(procs: list[Process]) -> Schedule:
    """Shortest job first (non-preemptive); ties by arrival order."""
    burst = {p.pid: p.burst for p in procs}
    return _simulate(procs, lambda q, rem, now: min(q, key=lambda pid: (burst[pid], q.index(pid))))


def srtf(procs: list[Process]) -> Schedule:
    """Shortest remaining time first (preemptive SJF)."""
    return _simulate(procs, lambda q, rem, now: min(q, key=lambda pid: (rem[pid], q.index(pid))), preemptive_key=True)


def round_robin(procs: list[Process], quantum: int) -> Schedule:
    if quantum < 1:
        raise ValueError("quantum must be >= 1")
    return _simulate(procs, lambda q, rem, now: q[0], quantum=quantum)


def priority(procs: list[Process], preemptive: bool = False) -> Schedule:
    """Priority scheduling (smaller number = higher priority); ties by arrival order. No aging."""
    prio = {p.pid: p.priority for p in procs}
    return _simulate(procs, lambda q, rem, now: min(q, key=lambda pid: (prio[pid], q.index(pid))), preemptive_key=preemptive)
