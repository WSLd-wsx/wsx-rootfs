"""Verify image-local key material is removed without following symlinks."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('reset_keyring', ROOT/'scripts/reset-cachyos-keyring.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class KeyringTests(unittest.TestCase):
    def test_clear_local_identity_without_touching_official_keyring_packages(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'etc/pacman.d/gnupg').mkdir(parents=True)
            (root/'etc/os-release').write_text('ID=cachyos\n')
            (root/'etc/pacman.d/gnupg/pubring.kbx').write_text('fixture')
            official = root/'usr/share/pacman/keyrings/cachyos.gpg'
            official.parent.mkdir(parents=True)
            official.write_text('public fixture')
            module.reset(root)
            self.assertEqual(list((root/'etc/pacman.d/gnupg').iterdir()), [])
            self.assertEqual((root/'etc/pacman.d/gnupg').stat().st_mode & 0o777, 0o700)
            self.assertEqual(official.read_text(), 'public fixture')

    def test_reject_symlink_keyring(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'etc/pacman.d').mkdir(parents=True)
            (root/'etc/os-release').write_text('ID=cachyos\n')
            (root/'etc/pacman.d/gnupg').symlink_to('/tmp')
            with self.assertRaisesRegex(ValueError, 'keyring path'):
                module.reset(root)
