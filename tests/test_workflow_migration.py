"""Rootfs sources contain no active hosted workflows."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class WorkflowHistory(unittest.TestCase):
    def test_no_active_source_workflows(self):
        self.assertEqual(list((ROOT/'.github/workflows').glob('*.yml')),[])
        self.assertEqual(list((ROOT/'.github/workflows').glob('*.yaml')),[])

if __name__=='__main__': unittest.main()
