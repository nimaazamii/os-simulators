import random
import unittest

from ossim import (TLB, Process, clock, effective_access_time, fcfs, fifo, lru, optimal, priority, round_robin, sjf,
                   srtf)

# Textbook example (Silberschatz et al.): P1 0/24? -> use the classic 3-process FCFS example and the 4-process SJF/SRTF one.
CLASSIC = [Process("P1", 0, 24), Process("P2", 0, 3), Process("P3", 0, 3)]
FOUR = [Process("P1", 0, 8), Process("P2", 1, 4), Process("P3", 2, 9), Process("P4", 3, 5)]


def gantt(s):
    return [(p, a, b) for p, a, b in s.gantt]


class TestScheduling(unittest.TestCase):
    def test_fcfs_classic(self):
        s = fcfs(CLASSIC)
        self.assertEqual(gantt(s), [("P1", 0, 24), ("P2", 24, 27), ("P3", 27, 30)])
        self.assertEqual({k: v.waiting for k, v in s.results.items()}, {"P1": 0, "P2": 24, "P3": 27})
        self.assertAlmostEqual(s.averages()["waiting"], 17.0)

    def test_sjf_and_srtf_four_process_example(self):
        sj, sr = sjf(FOUR), srtf(FOUR)
        self.assertEqual(gantt(sj), [("P1", 0, 8), ("P2", 8, 12), ("P4", 12, 17), ("P3", 17, 26)])
        self.assertAlmostEqual(sj.averages()["waiting"], (0 + 7 + 15 + 9) / 4)
        self.assertEqual(sr.results["P1"].completion, 17)                         # preempted by P2
        self.assertAlmostEqual(sr.averages()["waiting"], 6.5)                      # (9 + 0 + 15 + 2) / 4
        self.assertLess(sr.averages()["waiting"], sj.averages()["waiting"])

    def test_round_robin_quantum_4(self):
        s = round_robin(CLASSIC, 4)
        self.assertEqual(gantt(s), [("P1", 0, 4), ("P2", 4, 7), ("P3", 7, 10), ("P1", 10, 30)])
        self.assertAlmostEqual(s.averages()["waiting"], (6 + 4 + 7) / 3)
        self.assertEqual(s.results["P2"].response, 4)
        self.assertEqual(s.context_switches, 3)

    def test_round_robin_large_quantum_equals_fcfs(self):
        a, b = round_robin(FOUR, 1000), fcfs(FOUR)
        self.assertEqual({k: v.completion for k, v in a.results.items()}, {k: v.completion for k, v in b.results.items()})

    def test_priority_preemptive_vs_not(self):
        procs = [Process("A", 0, 10, 3), Process("B", 1, 5, 1), Process("C", 2, 2, 2)]
        np_ = priority(procs)
        self.assertEqual([g[0] for g in np_.gantt], ["A", "B", "C"])
        p = priority(procs, preemptive=True)
        self.assertEqual(gantt(p), [("A", 0, 1), ("B", 1, 6), ("C", 6, 8), ("A", 8, 17)])

    def test_idle_time_and_utilization(self):
        s = fcfs([Process("A", 0, 2), Process("B", 5, 2)])
        self.assertEqual(gantt(s), [("A", 0, 2), ("idle", 2, 5), ("B", 5, 7)])
        self.assertAlmostEqual(s.cpu_utilization, 4 / 7)
        self.assertEqual(s.makespan, 7)

    def test_invariants_on_random_workloads(self):
        rng = random.Random(0)
        for _ in range(30):
            procs = [Process(f"P{i}", rng.randint(0, 10), rng.randint(1, 8), rng.randint(0, 3)) for i in range(rng.randint(1, 6))]
            for s in (fcfs(procs), sjf(procs), srtf(procs), round_robin(procs, rng.randint(1, 5)), priority(procs), priority(procs, True)):
                for r in s.results.values():
                    self.assertGreaterEqual(r.waiting, 0)
                    self.assertGreaterEqual(r.start, r.arrival)
                    self.assertGreaterEqual(r.completion - r.arrival, r.burst)
                cpu = sum(e - st for pid, st, e in s.gantt if pid != "idle")
                self.assertEqual(cpu, sum(p.burst for p in procs))                  # work is conserved
                for (_, _, e1), (_, s2, _) in zip(s.gantt, s.gantt[1:]):
                    self.assertEqual(e1, s2)                                          # gantt chart is contiguous
            # SRTF minimises average waiting time among these algorithms
            self.assertLessEqual(srtf(procs).averages()["waiting"], sjf(procs).averages()["waiting"] + 1e-9)
            self.assertLessEqual(srtf(procs).averages()["waiting"], fcfs(procs).averages()["waiting"] + 1e-9)

    def test_validation(self):
        for bad in ([], [Process("A", 0, 0)], [Process("A", 0, 1), Process("A", 1, 1)], [Process("A", -1, 1)]):
            with self.assertRaises(ValueError):
                fcfs(bad)
        with self.assertRaises(ValueError):
            round_robin(CLASSIC, 0)


class TestPaging(unittest.TestCase):
    TEXTBOOK = [7, 0, 1, 2, 0, 3, 0, 4, 2, 3, 0, 3, 2, 1, 2, 0, 1, 7, 0, 1]     # Silberschatz reference string, 3 frames
    BELADY = [1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5]

    def test_textbook_fault_counts(self):
        self.assertEqual(fifo(self.TEXTBOOK, 3).faults, 15)
        self.assertEqual(lru(self.TEXTBOOK, 3).faults, 12)
        self.assertEqual(optimal(self.TEXTBOOK, 3).faults, 9)

    def test_beladys_anomaly_for_fifo_but_not_lru(self):
        self.assertEqual(fifo(self.BELADY, 3).faults, 9)
        self.assertEqual(fifo(self.BELADY, 4).faults, 10)              # more frames, more faults
        self.assertLessEqual(lru(self.BELADY, 4).faults, lru(self.BELADY, 3).faults)

    def test_optimal_is_a_lower_bound_and_lru_is_monotone(self):
        rng = random.Random(1)
        for _ in range(40):
            refs = [rng.randint(0, 7) for _ in range(60)]
            for f in range(1, 7):
                opt = optimal(refs, f).faults
                for algo in (fifo, lru, clock):
                    self.assertGreaterEqual(algo(refs, f).faults, opt)
            lru_faults = [lru(refs, f).faults for f in range(1, 9)]
            self.assertEqual(lru_faults, sorted(lru_faults, reverse=True))      # stack algorithm: no anomaly
            self.assertEqual(lru(refs, 8).faults, len(set(refs)))               # enough frames: only compulsory faults

    def test_clock_behaviour(self):
        # hand trace: after 1,2,3 all bits are set; the hit on 1 keeps its bit; page 4 sweeps the hand once, clearing every
        # bit, and replaces the first frame (page 1); so the next access to 1 faults and replaces 2 (hand at frame 1)
        r = clock([1, 2, 3, 1, 4, 1, 2], 3)
        self.assertEqual(r.fault_flags, [True, True, True, False, True, True, True])
        self.assertEqual(r.frames_history[4], [4, 2, 3])
        self.assertEqual(clock([1, 1, 1, 1], 2).faults, 1)

    def test_history_and_rates(self):
        r = lru([1, 2, 1, 3], 2)
        self.assertEqual(r.fault_flags, [True, True, False, True])
        self.assertEqual(r.frames_history[-1], [1, 3])
        self.assertAlmostEqual(r.fault_rate, 0.75)
        self.assertEqual(r.faults + r.hits, 4)

    def test_validation(self):
        with self.assertRaises(ValueError):
            fifo([1, 2], 0)
        with self.assertRaises(ValueError):
            lru([-1], 2)


class TestTLB(unittest.TestCase):
    def test_hits_misses_and_lru_eviction(self):
        tlb = TLB(2)
        table = {p: p * 10 for p in range(5)}
        for p in (0, 1, 0, 2, 1):                    # 0 m, 1 m, 0 h, 2 m (evict 1), 1 m
            self.assertEqual(tlb.lookup(p, table.get), table[p])
        self.assertEqual((tlb.hits, tlb.misses), (1, 4))
        self.assertAlmostEqual(tlb.hit_rate, 0.2)

    def test_effective_access_time(self):
        self.assertAlmostEqual(effective_access_time(0.98, 20, 100), 0.98 * 120 + 0.02 * 220)
        self.assertAlmostEqual(effective_access_time(1.0, 0, 100), 100.0)
        with self.assertRaises(ValueError):
            effective_access_time(1.5, 1, 1)
        with self.assertRaises(ValueError):
            TLB(0)


if __name__ == "__main__":
    unittest.main()
