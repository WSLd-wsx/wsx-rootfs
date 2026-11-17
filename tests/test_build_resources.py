"""Concurrency must not exceed CPU or memory budgets."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from build_resources import select_jobs


class ResourceTests(unittest.TestCase):
    def test_cpu_and_memory_bounds(self):
        gib = 1024 ** 3
        self.assertEqual(select_jobs(2, 7 * gib), 2)
        self.assertEqual(select_jobs(4, 16 * gib), 4)
        self.assertEqual(select_jobs(16, 8 * gib), 3)
        self.assertEqual(select_jobs(2, gib), 1)
