import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from package_source_inventory import create, collect_known_sources


class PackageSourceInventoryTests(unittest.TestCase):
    def test_accepts_arch_prerelease_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); package = root/'var/lib/pacman/local/foo'; package.mkdir(parents=True)
            (package/'desc').write_text('%NAME%\nfoo\n\n%VERSION%\n2.0~rc1-1\n\n%LICENSE%\nMIT\n')
            (package/'files').write_text('%FILES%\n')
            result = create(root, ['foo 2.0~rc1-1'], [])
            self.assertEqual(result['packages'][0]['version'], '2.0~rc1-1')

    def test_tracks_source_discovery_without_claiming_correspondence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); package = root/'var/lib/pacman/local/libfoo-2.0-1'; package.mkdir(parents=True)
            desc = b'%NAME%\nlibfoo\n\n%BASE%\nfoo\n\n%VERSION%\n2.0-1\n\n%LICENSE%\nMIT\n\n%URL%\nhttps://example.org/foo\n'
            (package/'desc').write_bytes(desc); (package/'files').write_bytes(b'%FILES%\nusr/lib/libfoo.so\n')
            result = create(root, ['libfoo 2.0-1'], ['extra libfoo 2.0-1 [installed]'])
            record = result['packages'][0]
            self.assertEqual(record['description_sha256'], hashlib.sha256(desc).hexdigest())
            self.assertEqual(record['package_base'], 'foo')
            self.assertEqual(record['repositories_observed'], ['extra'])
            self.assertIn('/packages/foo/', record['source_candidates'][0]['url'])
            self.assertEqual(record['source_candidates'][0]['status'], 'discovery_only')
            self.assertEqual(result['source_completeness'], 'not_verified')
            with self.assertRaisesRegex(ValueError, 'differs from recorded'):
                create(root, ['libfoo 1.0-1'], [])

    def test_collects_verified_sources_and_handles_missing_without_clearance(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)/'rootfs'; root.mkdir(); work = Path(tmp)/'work'; work.mkdir()
            for path, data in [('usr/lib/lib.so', b'binary'), ('usr/share/licenses/NOTICE', b'notice')]:
                file = root/path; file.parent.mkdir(parents=True, exist_ok=True); file.write_bytes(data)
            pin = {'version': '3.0.0-1', 'library': 'usr/lib/lib.so', 'library_sha256': hashlib.sha256(b'binary').hexdigest(),
                   'notice': 'usr/share/licenses/NOTICE', 'notice_sha256': hashlib.sha256(b'notice').hexdigest(),
                   'sources': (('upstream.tar.gz', 'https://example.org/source', hashlib.sha256(b'source').hexdigest()),
                               ('packaging.tar.gz', 'https://example.org/recipe', hashlib.sha256(b'packaging').hexdigest()))}
            inventory = {'packages': [{'name': 'libfdk-aac', 'version': '3.0.0-1', 'source_correspondence': 'not_verified'}]}
            with patch('package_source_inventory.FDK', pin), patch('urllib.request.urlopen', side_effect=[io.BytesIO(b'source'), io.BytesIO(b'packaging')]):
                collect_known_sources(root, inventory, work)
            row = inventory['packages'][0]; self.assertEqual(row['retained_source_status'], 'matching_library_source_retained')
            self.assertEqual(row['source_correspondence'], 'not_verified')
            receipt = json.loads((work/'package-source-evidence/manifest.json').read_text())
            self.assertEqual(receipt['binary_sha256'], hashlib.sha256(b'binary').hexdigest())
            self.assertEqual((work/'package-source-evidence/upstream.tar.gz').read_bytes(), b'source')
            second = Path(tmp)/'second'; second.mkdir()
            with patch('package_source_inventory.FDK', pin), patch('urllib.request.urlopen', side_effect=OSError('offline')):
                collect_known_sources(root, inventory, second)
            self.assertEqual(row['retained_source_status'], 'unavailable_or_hash_mismatch')
            self.assertNotIn('retained_source_manifest', row)
            self.assertFalse((second/'package-source-evidence').exists())
            third = Path(tmp)/'third'; third.mkdir()
            with patch('package_source_inventory.FDK', pin), patch('urllib.request.urlopen', side_effect=[io.BytesIO(b'wrong')]):
                collect_known_sources(root, inventory, third)
            self.assertEqual(row['retained_source_status'], 'unavailable_or_hash_mismatch')
            self.assertFalse((third/'package-source-evidence').exists())
            (root/'usr/lib/lib.so').write_bytes(b'other binary')
            with patch('package_source_inventory.FDK', pin), patch('urllib.request.urlopen') as download:
                collect_known_sources(root, inventory, third)
            self.assertEqual(row['retained_source_status'], 'binary_or_notice_not_matched')
            download.assert_not_called()

    def test_rejects_untrusted_metadata_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); package = root/'var/lib/pacman/local/foo'; package.mkdir(parents=True)
            (package/'files').write_text('%FILES%\n'); (package/'desc').symlink_to('/etc/passwd')
            with self.assertRaisesRegex(ValueError, 'Unsafe installed package metadata'):
                create(root, [], [])


if __name__ == '__main__': unittest.main()
