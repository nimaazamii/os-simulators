"""ossim: CPU scheduling and virtual-memory (paging, TLB) simulators."""
from .paging import TLB, PagingResult, clock, effective_access_time, fifo, lru, optimal
from .scheduling import Process, ProcessResult, Schedule, fcfs, priority, round_robin, sjf, srtf

__version__ = "0.1.0"
__all__ = ["Process", "ProcessResult", "Schedule", "TLB", "PagingResult", "clock", "effective_access_time", "fcfs", "fifo",
           "lru", "optimal", "priority", "round_robin", "sjf", "srtf"]
