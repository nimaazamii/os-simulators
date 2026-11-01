# os-simulators

Two operating-system simulators in pure Python: **CPU scheduling** and **virtual memory**.

* **Scheduling:** FCFS, SJF, SRTF, Round Robin (any quantum), priority (non-preemptive and preemptive). Output: Gantt chart, waiting/turnaround/response times, context switches, CPU utilisation (idle time is modelled).
* **Paging:** FIFO, LRU, Belady's optimal (OPT), Clock (second chance), frame-by-frame history, a fully associative LRU TLB and effective access time.

## Installation and quick start
```bash
git clone https://github.com/nimaazamii/os-simulators.git
cd os-simulators
pip install -e ".[dev]"
pytest -q
```

```python
from ossim import Process, fcfs, round_robin, fifo, lru, optimal
procs = [Process("P1", 0, 24), Process("P2", 0, 3), Process("P3", 0, 3)]
s = round_robin(procs, 4)
print(s.gantt)
print({k: round(v, 2) for k, v in s.averages().items()})
refs = [7, 0, 1, 2, 0, 3, 0, 4, 2, 3, 0, 3, 2, 1, 2, 0, 1, 7, 0, 1]
print(fifo(refs, 3).faults, lru(refs, 3).faults, optimal(refs, 3).faults)
```
Output:
```
[('P1', 0, 4), ('P2', 4, 7), ('P3', 7, 10), ('P1', 10, 30)]
{'waiting': 5.67, 'turnaround': 15.67, 'response': 3.67}
15 12 9
```

## Verification (`pytest -q`, 16 tests)
Textbook examples (FCFS waiting times 0/24/27; RR quantum 4 Gantt chart; the 20-reference string gives 15/12/9 faults for FIFO/LRU/OPT; Belady's anomaly 9 -> 10 faults for FIFO with 3 -> 4 frames),
plus **invariants on random workloads**: work is conserved, Gantt charts are contiguous, waiting times are non-negative, SRTF never has a higher average waiting time than SJF or FCFS,
OPT is a lower bound for every other policy, LRU never exhibits the anomaly (stack property), and with enough frames only compulsory faults remain.

## Experiments (`python examples/run_experiments.py`; synthetic workloads, seed 0)
12 random processes (arrival 0-20, burst 2-15, priority 0-4):

| algorithm | avg waiting | avg turnaround | avg response | context switches |
|---|---|---|---|---|
| FCFS | 39.42 | 49.00 | 39.42 | 11 |
| SJF | 31.58 | 41.17 | 31.58 | 11 |
| SRTF | 31.58 | 41.17 | 31.25 | 12 |
| RR q=2 | 61.92 | 71.50 | 9.17 | 58 |
| RR q=8 | 50.67 | 60.25 | 29.83 | 17 |
| Priority | 36.42 | 46.00 | 36.42 | 11 |
| Priority (preemptive) | 45.33 | 54.92 | 24.08 | 70 |

Round Robin gives the best response time but the worst waiting time here; SJF/SRTF minimise waiting time (as theory predicts) at the cost of starvation risk for long jobs (no aging is implemented).

Paging on the textbook string with 3 frames: {'fifo': 15, 'lru': 12, 'clock': 14, 'optimal': 9}. Belady's anomaly: FIFO faults {'3': 9, '4': 10, '5': 5} versus LRU {'3': 10, '4': 8, '5': 5} for 3/4/5 frames.
Fault rate on a synthetic 480-reference string with phase-wise locality:

| frames | FIFO | LRU | Clock | OPT |
|---|---|---|---|---|
| 3 | 0.385 | 0.381 | 0.396 | 0.252 |
| 5 | 0.083 | 0.077 | 0.079 | 0.075 |
| 8 | 0.069 | 0.071 | 0.069 | 0.069 |
| 12 | 0.069 | 0.069 | 0.069 | 0.060 |

## Limitations and future work
Unit-time simulation (no I/O bursts, no context-switch cost, no multilevel queues or multiprocessors); single-level page table and no dirty-page/write-back model; all workloads are synthetic.

## References
* Silberschatz, Galvin and Gagne, *Operating System Concepts*; Belady, Nelson and Shedler (1969) An anomaly in space-time characteristics of certain programs running in a paging machine. CACM 12(6).

## License
MIT, see `LICENSE`.
