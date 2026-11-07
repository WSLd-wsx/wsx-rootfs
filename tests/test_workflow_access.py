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

    def test_public_binary_guard_precedes_build_and_protects_always_uploads(self):
        for name in ('cachyos-plasma.yml',):
            text = (ROOT/'components/workflow-history/20261107'/name).read_text()
            self.assertIn('scripts/check-workflow-access.py', text)
            self.assertIn('--operation cachyos-candidate', text)
            self.assertIn("if: ${{ always() && steps.access.outcome == 'success' && github.event.repository.private }}", text)
        checks = (ROOT/'components/workflow-history/20261107/contracts.yml').read_text()
        self.assertIn('--operation source-check', checks)

    def test_components_allow_public_builds_but_not_public_diagnostics(self):
        access.authorize(access.REPOSITORY, dict(full_name=access.REPOSITORY,private=False), 'component-build')
        with self.assertRaises(ValueError):
            access.authorize('other/repo',dict(full_name='other/repo',private=False),'component-build')
        text=(ROOT/'components/workflow-history/20261107/components.yml').read_text()
        self.assertIn('--operation component-build',text)
        self.assertIn("steps.access.outcome == 'success' && github.event.repository.private",text)
        self.assertLess(text.index('Verify existing private component destination'),text.index('Build pinned private source closure'))

    def test_explicit_omarchy_candidate_route_keeps_attachments_private(self):
        access.authorize(access.REPOSITORY,dict(full_name=access.REPOSITORY,private=False),'omarchy-candidate')
        text=(ROOT/'components/workflow-history/20261107/build-rootfs.yml').read_text()
        self.assertIn('--operation omarchy-candidate',text)
        self.assertIn('--public-prerelease',text)
        self.assertIn('scripts/check-shared-sources.py',text)
        self.assertIn("steps.access.outcome == 'success' && github.event.repository.private",text)
