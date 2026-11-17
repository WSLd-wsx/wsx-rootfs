import unittest
from unittest.mock import patch
from review_index import create


class ReviewIndexTest(unittest.TestCase):
    def test_links_identity_and_reports_unverified_sources(self):
        manifest = dict(asset_name='image.tar.zst', sha256='a' * 64,
                        build_commit='b' * 40, build_identity='c' * 64)
        sources = dict(rootfs_packages=['libfdk-aac 3.0.0-1', 'other 1'],
                       component_source_delivery={'shared_source': {'tag': 'source-tag'}})
        with patch.dict('os.environ', {'GITHUB_SHA': 'd' * 40, 'GITHUB_RUN_ID': '42'}, clear=True):
            index = create(manifest, sources)
        self.assertEqual(index['image']['sha256'], manifest['sha256'])
        self.assertEqual(index['workflow']['commit'], 'd' * 40)
        self.assertEqual(index['graphics_source']['tag'], 'source-tag')
        self.assertEqual(index['known_source_requirements'][0]['version'], '3.0.0-1')
        self.assertEqual(index['known_source_requirements'][0]['corresponding_source_status'], 'not_verified')
        self.assertEqual(index['source_completeness'], 'not_verified')

    def test_unavailable_workflow_and_package_are_not_invented(self):
        manifest = dict(asset_name='image', sha256='a', build_commit='b', build_identity='c')
        sources = dict(rootfs_packages=['other 1'], component_source_delivery={})
        with patch.dict('os.environ', {'GITHUB_SHA': 'invalid'}, clear=True):
            index = create(manifest, sources)
        self.assertIsNone(index['workflow']['commit'])
        self.assertEqual(index['known_source_requirements'], [])
