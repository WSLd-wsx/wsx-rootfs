"""Exercise negotiated Plasma graphics selection with isolated fixture files."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import sys
from types import SimpleNamespace
import unittest
import uuid
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('stage_cachyos', ROOT/'scripts/stage-cachyos.py')
stage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage)


def fixture(directory, files, **metadata):
    hashes = {}
    for name in files:
        path = directory/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'fixture')
        hashes[name] = hashlib.sha256(b'fixture').hexdigest()
    (directory/'manifest.json').write_text(json.dumps(dict(files=hashes, **metadata)))


class PlasmaStageTests(unittest.TestCase):


    def test_staging_records_exact_package_versions(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            root = work/'root'
            (root/'usr/bin').mkdir(parents=True)
            (root/'usr/lib').mkdir(parents=True)
            helper = root/'usr/lib/plasma-setup-xwayland'
            helper.write_text('fixture')
            helper.chmod(0o755)
            components = work/'private'
            for name in ('mesa', 'venus', 'kwin-opaque'):
                (components/name).mkdir(parents=True)
                (components/name/'manifest.json').write_text(json.dumps({'version':'fixture','files':{'fixture':'a'*64}}))
            (work/'rootfs-packages.txt').write_text('kwin 6.8.1-2\nplasma-workspace 6.8.1-1\nqt6-base 6.12.0-3\n')
            with patch.object(sys, 'argv', ['stage', str(root), str(components)]), patch.object(stage.subprocess, 'run'):
                stage.main()
            for name in ('bootstrap-v2.py', 'adapter-store.py'):
                self.assertTrue((root/'usr/lib/wsx'/name).is_file())
            for name in ('guest-protocol.py', 'protocol-display.py', 'protocol-retirement.py', 'device-view.py'):
                self.assertFalse((root/'usr/lib/wsx'/name).exists())
            self.assertFalse((root/'usr/bin/wsx-guest').exists())
            self.assertFalse((root/'usr/lib/wsx/runtime/desktop.py').exists())
            profile = json.loads((root/'usr/lib/wsx/guest-profile.json').read_text())
            self.assertEqual(profile['implementation'], 'plasma')
            self.assertEqual(set(profile['component_manifests']), {'mesa','venus','kwin-opaque'})
            lock = json.loads((root/'usr/lib/wsx/plasma-compat.json').read_text())
            self.assertEqual(lock['cpu_architecture_level'], 'x86-64-v3')
            self.assertEqual(lock['packages']['kwin'], '6.8.1-2')
            self.assertEqual(str((root/'opt/wsx/kwin-opaque-6.8.1/lib/libexec/plasma-setup-xwayland').readlink()), '/usr/lib/plasma-setup-xwayland')
