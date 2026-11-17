"""Discover unpublished source releases without relying on tag resolution."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
spec=importlib.util.spec_from_file_location('prepare_shared',Path(__file__).resolve().parents[1]/'scripts/prepare-shared-sources.py')
prepare=importlib.util.module_from_spec(spec);spec.loader.exec_module(prepare)


class DraftDiscovery(unittest.TestCase):
    def test_publication_only_promotes_verified_matching_draft(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); (root/prepare.INDEX).write_bytes(b'index')
            index={'tag':'graphics-sources-omarchy-test','profile':'omarchy'}
            pin={'tag':index['tag'],'manifest_sha256':prepare.sha(root/prepare.INDEX)}
            result=dict(pin,draft=True)
            with patch.object(prepare,'verify_bundle',return_value=index), \
                 patch.object(prepare,'api',return_value={'full_name':prepare.REPOSITORY,'private':False}), \
                 patch.object(prepare,'publish_draft',return_value=result), \
                 patch.object(prepare,'download_index',return_value=b'index'), \
                 patch.object(prepare,'gh') as gh:
                self.assertEqual(prepare.publish_public(root),pin)
                self.assertIn('--prerelease',gh.call_args.args)
                self.assertIn('--latest=false',gh.call_args.args)

    def test_publication_rejects_private_repository_before_upload(self):
        with patch.object(prepare,'verify_bundle',return_value={}), \
             patch.object(prepare,'api',return_value={'full_name':prepare.REPOSITORY,'private':True}), \
             patch.object(prepare,'publish_draft') as publish:
            with self.assertRaisesRegex(ValueError,'public repository'):
                prepare.publish_public(Path('/unused'))
            publish.assert_not_called()

    def test_explicit_pin_still_rejects_unapproved_run_repository(self):
        pin = {'run_repository': 'unapproved/repository'}
        with self.assertRaisesRegex(ValueError, 'Unapproved component workflow repository'):
            prepare.acquire('omarchy', Path('/unused'), pin)

    def test_draft_discovery_uses_release_id_after_eventual_visibility(self):
        draft=dict(id=123,tag_name='fixture',draft=True)
        with patch.object(prepare,'releases',side_effect=[[],[draft]]), patch.object(prepare,'api',return_value=draft) as api,patch.object(prepare.time,'sleep'):
            self.assertEqual(prepare.find_release('fixture'),draft)
        self.assertTrue(api.call_args_list[-1].args[0].endswith('/releases/123'))
        self.assertTrue(all('/releases/tags/' not in call.args[0] for call in api.call_args_list))

    def test_duplicate_release_rejected(self):
        draft=dict(id=123,tag_name='fixture',draft=True)
        with patch.object(prepare,'releases',return_value=[draft,draft]):
            with self.assertRaisesRegex(ValueError,'Duplicate'):prepare.find_release('fixture')
