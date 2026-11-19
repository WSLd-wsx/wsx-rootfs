"""Only approved rootfs workflows live in the source repository."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class WorkflowHistory(unittest.TestCase):
    def test_approved_rootfs_workflows_are_present(self):
        self.assertEqual(
            {p.name for p in (ROOT / '.github/workflows').glob('*.yml')},
            {'components.yml', 'omarchy.yml', 'promote-rootfs.yml'},
        )
        self.assertEqual(list((ROOT/'.github/workflows').glob('*.yaml')),[])

if __name__=='__main__': unittest.main()
