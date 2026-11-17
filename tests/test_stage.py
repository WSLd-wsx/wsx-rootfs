"""Verify the Omarchy image stages only the v2 bootstrap interface."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('stage_guest', ROOT / 'scripts/stage-guest.py')
stage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage)


class StageTests(unittest.TestCase):
    def test_image_does_not_embed_external_adapter(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'root'
            (root / 'usr/bin').mkdir(parents=True)
            components = Path(tmp) / 'components'
            for name in ('mesa', 'venus', 'opaque-consumer'):
                (components / name).mkdir(parents=True)
                (components / name / 'manifest.json').write_text(json.dumps({'version': 'fixture'}))
            with patch.object(sys, 'argv', ['stage', str(root), str(components)]), patch.object(stage.subprocess, 'run'):
                stage.main()
            base = root / 'usr/lib/wsx'
            for name in ('bootstrap-v2.py', 'adapter-store.py', 'guest-profile.json', 'initialize-user.sh'):
                self.assertTrue((base / name).is_file(), name)
            for name in ('guest-protocol.py', 'protocol-display.py', 'protocol-retirement.py', 'device-view.py', 'runtime/desktop.py'):
                self.assertFalse((base / name).exists(), name)
            self.assertFalse((root / 'usr/bin/wsx-guest').exists())


if __name__ == '__main__': unittest.main()
