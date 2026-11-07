"""Inactive historical workflow bytes remain verifiable after orchestration moves."""
import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
HISTORY = ROOT/'components/workflow-history/20261107'

class WorkflowHistory(unittest.TestCase):
    def test_snapshot_preserves_all_original_workflow_hashes(self):
        metadata=json.loads((HISTORY/'snapshot.json').read_text())
        self.assertEqual(metadata['source_repository'],'WSLd-wsx/wsx-rootfs')
        self.assertEqual(len(metadata['files']),12)
        for name, expected in metadata['files'].items():
            with self.subTest(name=name):
                self.assertEqual(hashlib.sha256((HISTORY/name).read_bytes()).hexdigest(),expected)
    def test_no_active_source_workflows(self):
        self.assertEqual(list((ROOT/'.github/workflows').glob('*.yml')),[])
        self.assertEqual(list((ROOT/'.github/workflows').glob('*.yaml')),[])

if __name__=='__main__': unittest.main()
