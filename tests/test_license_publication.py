"""Prevent candidate binary uploads from bypassing the current license review."""
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parents[1]


class ComponentDistributionReviewTests(unittest.TestCase):
    def test_component_uploads_require_review_when_distribution_enabled(self):
        for filename,upload in (
            ('components.yml','Upload and verify paired private GHCR package'),
        ):
            with self.subTest(workflow=filename):
                text=(ROOT/'components/workflow-history/20261107'/filename).read_text()
                steps=re.split(r'^      - name: ',text,flags=re.MULTILINE)[1:]
                index=next(i for i,s in enumerate(steps) if s.splitlines()[0]==upload)
                self.assertGreater(index,0)
                gate=steps[index-1]
                self.assertEqual(gate.splitlines()[0],'Require private component artifact checks')
                self.assertIn('run: python3 scripts/private-artifact-gate.py',gate)
                self.assertNotIn('continue-on-error:',gate)
                self.assertIn('if: ${{ !inputs.test_only }}',gate)
                self.assertIn('if: ${{ !inputs.test_only }}',steps[index])
                self.assertRegex(text, r'test_only:[\s\S]*?default: true')
                self.assertNotIn('if: always()',steps[index])
                self.assertNotIn('if: success() ||',steps[index])

    def test_rootfs_workflows_do_not_republish_component_packages(self):
        for name in ('build-rootfs.yml','cachyos-plasma.yml'):
            text=(ROOT/'components/workflow-history/20261107'/name).read_text()
            self.assertNotIn('path: out/component-package/',text)
            self.assertIn('scripts/private-artifact-gate.py',text)
            self.assertNotIn('  publish:',text)
            if name == 'build-rootfs.yml':
                self.assertIn('--public-prerelease', text)
                self.assertLess(text.index('scripts/private-artifact-gate.py'), text.index('scripts/publish.py --repo'))
            else:
                self.assertIn('scripts/publish.py --repo',text)
                self.assertIn('--public-prerelease',text)
                self.assertNotIn('actions/download-artifact@',text)
