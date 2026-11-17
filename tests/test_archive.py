import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from archive import check_hygiene, pack


class HygieneTests(unittest.TestCase):
    def test_private_data_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); (root/'home/user').mkdir(parents=True)
            with self.assertRaises(ValueError):
                check_hygiene(root)

    def test_credential_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); (root/'.netrc').write_text('fixture')
            with self.assertRaises(ValueError):
                check_hygiene(root)


@unittest.skipUnless(os.geteuid() == 0 and shutil.which('zstd'), 'Requires root and zstd; exercised in CI')
class MetadataTests(unittest.TestCase):
    def test_real_roundtrip(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary); root = base/'root'; root.mkdir()
            binary = root/'usr/bin/tool'; binary.parent.mkdir(parents=True)
            shutil.copy2('/usr/bin/true', binary)
            binary.chmod(0o751); os.chown(binary, 1234, 2345)
            os.setxattr(binary, 'user.wsx-test', b'fixture')
            subprocess.run(['setfacl', '-m', 'u:3456:r-x', str(binary)], check=True)
            subprocess.run(['setcap', 'cap_net_bind_service=ep', str(binary)], check=True)
            os.link(binary, binary.with_name('hardlink'))
            binary.with_name('link').symlink_to('tool')
            report = pack(root, base/'image.tar.zst', level=3, threads=1)
            self.assertTrue(report['passed'])
            self.assertGreater(report['compression_peak_rss_kib'], 0)
            with self.assertRaises(ValueError):
                pack(root, base/'image.tar.zst')

    def test_stream_mode_needs_evidence_and_does_not_claim_metadata_check(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary); root = base/'root'; root.mkdir()
            (root/'file').write_text('fixture')
            with self.assertRaisesRegex(ValueError, 'evidence'):
                pack(root, base/'missing.tar.zst', policy={'mode':'stream'})
            report = pack(root, base/'stream.tar.zst', level=3, threads=1,
                          policy={'mode':'stream','recipe_fingerprint':'a'*64,
                                  'evidence':{'release_id':1}})
            self.assertEqual(report['verification_mode'], 'stream')
            self.assertEqual(report['verified'], ['zstd_stream'])
            self.assertIsNone(report['metadata_entries'])
