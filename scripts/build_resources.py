"""Bound compiler concurrency by available CPUs and memory, with evidence."""
import os
from pathlib import Path


def select_jobs(cpus, available_bytes):
    # Leave room for linking, the OS and build tools; large C++ units can be costly.
    gib = 1024 ** 3
    memory_jobs = max(1, (available_bytes - 2 * gib) // (2 * gib))
    return max(1, min(cpus, memory_jobs))


def resources():
    cpus = len(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else (os.cpu_count() or 1)
    memory = dict(line.split(':', 1) for line in Path('/proc/meminfo').read_text().splitlines())
    available = int(memory['MemAvailable'].split()[0]) * 1024
    # Docker may expose host totals despite cgroup limits.
    maximum = Path('/sys/fs/cgroup/memory.max')
    current = Path('/sys/fs/cgroup/memory.current')
    if maximum.exists() and maximum.read_text().strip() != 'max':
        available = min(available, max(0, int(maximum.read_text()) - int(current.read_text())))
    quota = Path('/sys/fs/cgroup/cpu.max')
    if quota.exists():
        amount, period = quota.read_text().split()
        if amount != 'max':
            cpus = min(cpus, max(1, int(amount) // int(period)))
    return dict(cpus=cpus, available_bytes=available, jobs=select_jobs(cpus, available))
