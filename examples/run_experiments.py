"""Scheduling and paging experiments; writes results/experiments.json.

    python examples/run_experiments.py
"""
from __future__ import annotations

import json
import random
from pathlib import Path

from ossim import Process, clock, fcfs, fifo, lru, optimal, priority, round_robin, sjf, srtf

OUT = Path(__file__).resolve().parents[1] / "results"
OUT.mkdir(exist_ok=True)


def main() -> None:
    rng = random.Random(0)
    procs = [Process(f"P{i}", rng.randint(0, 20), rng.randint(2, 15), rng.randint(0, 4)) for i in range(12)]
    algos = {"FCFS": fcfs(procs), "SJF": sjf(procs), "SRTF": srtf(procs), "RR q=2": round_robin(procs, 2),
             "RR q=8": round_robin(procs, 8), "Priority": priority(procs), "Priority (preemptive)": priority(procs, True)}
    sched = {name: {**{k: round(v, 3) for k, v in s.averages().items()}, "context_switches": s.context_switches,
                    "cpu_utilization": round(s.cpu_utilization, 3), "makespan": s.makespan} for name, s in algos.items()}

    textbook = [7, 0, 1, 2, 0, 3, 0, 4, 2, 3, 0, 3, 2, 1, 2, 0, 1, 7, 0, 1]
    belady = [1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5]
    locality = []                                   # synthetic reference string with locality (working sets of 5 pages)
    for phase in range(8):
        base = rng.randint(0, 40)
        locality += [base + rng.choice([0, 0, 1, 1, 2, 3, 4]) for _ in range(60)]
    paging = {
        "textbook_20_refs_3_frames_faults": {a.__name__: a(textbook, 3).faults for a in (fifo, lru, clock, optimal)},
        "belady_FIFO_faults_by_frames": {str(f): fifo(belady, f).faults for f in (3, 4, 5)},
        "belady_LRU_faults_by_frames": {str(f): lru(belady, f).faults for f in (3, 4, 5)},
        "locality_trace_480_refs_fault_rate_by_frames": {
            str(f): {a.__name__: round(a(locality, f).fault_rate, 3) for a in (fifo, lru, clock, optimal)} for f in (3, 5, 8, 12)},
    }
    res = {"DATA": "synthetic workloads (seed 0), 12 random processes", "scheduling_averages": sched, "paging": paging}
    (OUT / "experiments.json").write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
