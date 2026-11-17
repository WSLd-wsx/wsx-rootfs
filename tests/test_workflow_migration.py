"""Only the approved rootfs build workflow lives in the source repository."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class WorkflowHistory(unittest.TestCase):
    def test_only_omarchy_workflow_is_present(self):
        self.assertEqual([p.name for p in (ROOT/'.github/workflows').glob('*.yml')],['omarchy.yml'])
        self.assertEqual(list((ROOT/'.github/workflows').glob('*.yaml')),[])

if __name__=='__main__': unittest.main()
