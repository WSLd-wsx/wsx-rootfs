"""Check fixed upstream inputs and explicit candidate snapshot admission."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]

class CachyosRecipeTests(unittest.TestCase):
    def test_official_source_hashes_and_gui_manager(self):
        directory = ROOT/'distros/cachyos-plasma'
        source = json.loads((directory/'upstream/source.json').read_text())
        for section in (source['files'], source['iso_identity']['files']):
            for name, expected in section.items():
                self.assertEqual(hashlib.sha256((directory/'upstream'/name).read_bytes()).hexdigest(), expected)
        packages = (directory/'packages.txt').read_text().splitlines()
        for required in ('shelly', 'plasma-desktop', 'plasma-workspace', 'cachyos-kde-settings'):
            self.assertIn(required, packages)
        self.assertNotIn('linux-cachyos', packages)

    def test_invalid_snapshot_fails_before_network(self):
        result = subprocess.run([sys.executable, str(ROOT/'scripts/prepare-cachyos.py'),
            '--snapshot', '2026.2.30', '--revision', '1', '--repo', 'x/y',
            '--output', '/tmp/invalid-snapshot-build.json'], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('day is out of range', result.stderr)

    def test_identity_license_and_retired_reference_scope(self):
        directory = ROOT/'distros/cachyos-plasma'
        source = json.loads((directory/'upstream/source.json').read_text())
        license_record = source['iso_identity']['license']
        self.assertEqual(license_record['expression'], 'GPL-3.0-only')
        self.assertEqual(hashlib.sha256((ROOT/license_record['path']).read_bytes()).hexdigest(),
                         license_record['sha256'])
        self.assertNotIn('netinstall.yaml', source['files'])
        self.assertFalse((directory/'upstream/netinstall.yaml').exists())
        boundaries = json.loads((ROOT/'components/license-boundaries.json').read_text())
        self.assertFalse(any('distros/cachyos-plasma/upstream/netinstall.yaml' in paths
                             for paths in boundaries['dependencies'].values()))
