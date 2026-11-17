"""Reject the retired binary import without reading or extracting payloads."""
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class PackageImportTests(unittest.TestCase):
    def test_rejects_untrusted_archive_before_extraction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / 'components.tar.gz'
            archive.write_bytes(b'not the pinned archive')
            result = subprocess.run([sys.executable, str(ROOT/'scripts/import-component-package.py'),
                                     str(archive), str(root)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Historical component import is retired', result.stderr)
            self.assertFalse((root/'private').exists())
