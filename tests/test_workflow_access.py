"""Public source checks must not implicitly enable binary or diagnostic uploads."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('workflow_access', ROOT/'scripts/check-workflow-access.py')
access = importlib.util.module_from_spec(spec)
spec.loader.exec_module(access)


class AccessTests(unittest.TestCase):
    def test_public_source_checks_and_private_binary_builds(self):
        for private in (True, False):
            metadata = dict(full_name=access.REPOSITORY, private=private)
            access.authorize(access.REPOSITORY, metadata, 'source-check')
            if private:
                access.authorize(access.REPOSITORY, metadata, 'binary-build')
            else:
                with self.assertRaisesRegex(ValueError, 'Public source-only'):
                    access.authorize(access.REPOSITORY, metadata, 'binary-build')

    def test_visibility_and_repository_identity_fail_closed(self):
        for metadata in ({'full_name': access.REPOSITORY},
                         {'full_name': access.REPOSITORY, 'private': 'true'},
                         {'full_name': 'other/repo', 'private': True}):
            with self.assertRaises(ValueError):
                access.authorize(access.REPOSITORY, metadata, 'source-check')
        with self.assertRaises(ValueError):
            access.authorize('other/repo', {'full_name': 'other/repo', 'private': True}, 'binary-build')
