"""Network profiles must select complete exact matches and remain idempotent."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('network_installer', ROOT / 'vendor/wsx-proto/network/install.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class NetworkProfiles(unittest.TestCase):
    def test_reuse_allows_only_exact_recorded_provenance_update(self):
        sys.path.insert(0, str(ROOT / 'scripts'))
        self.addCleanup(sys.path.remove, str(ROOT / 'scripts'))
        spec = importlib.util.spec_from_file_location('reuse_network_test', ROOT / 'scripts/reuse-components.py')
        reuse = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(reuse)
        original = 'b3278806dd5622b36944dadf49031d540fccdc2ad87f6643e7d06b3e7b1d1b7e'
        self.assertTrue(reuse.collection_only_change(ROOT, 'docs/provenance.json', original))
        self.assertFalse(reuse.collection_only_change(ROOT, 'docs/provenance.json', '0' * 64))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'docs').mkdir()
            (root / 'docs/provenance.json').write_text('{}')
            self.assertFalse(reuse.collection_only_change(root, 'docs/provenance.json', original))

    def test_new_profile_requires_all_hashes_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            adapter = root / 'adapter'
            profile = adapter / 'omarchy-4.5.0'
            profile.mkdir(parents=True)
            source = root / 'source'
            source.mkdir()
            target = source / 'panel'
            target.write_text('before\n')
            other = source / 'wifi'
            other.write_text('unchanged\n')
            (profile / 'panel.patch').write_text('--- a/panel\n+++ b/panel\n@@ -1 +1 @@\n-before\n+after\n')
            sha = lambda text: hashlib.sha256(text.encode()).hexdigest()
            files = {'panel': {'before': sha('before\n'), 'after': sha('after\n')},
                     'wifi': {'before': sha('unchanged\n'), 'after': sha('unchanged\n')}}
            with patch.object(installer, '__file__', str(adapter / 'install.py')), \
                 patch.object(installer, 'PROFILE_450', files), \
                 patch.object(sys, 'argv', ['install.py', str(source)]):
                other.write_text('unexpected\n')
                with self.assertRaisesRegex(RuntimeError, 'differs from all reviewed'):
                    installer.main()
                self.assertEqual(target.read_text(), 'before\n')
                other.write_text('unchanged\n')
                installer.main()
                installer.main()
                self.assertEqual(target.read_text(), 'after\n')
                self.assertEqual((source / 'panel.before-wsx-network-omarchy-4.5.0').read_text(), 'before\n')


if __name__ == '__main__':
    unittest.main()
