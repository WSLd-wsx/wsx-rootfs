"""Discover unpublished source releases without relying on tag resolution."""
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
spec=importlib.util.spec_from_file_location('prepare_shared',Path(__file__).resolve().parents[1]/'scripts/prepare-shared-sources.py')
prepare=importlib.util.module_from_spec(spec);spec.loader.exec_module(prepare)


class DraftDiscovery(unittest.TestCase):
    def test_explicit_pin_still_rejects_unapproved_run_repository(self):
        pin = {'run_repository': 'unapproved/repository'}
        with self.assertRaisesRegex(ValueError, 'Unapproved component workflow repository'):
            prepare.acquire('omarchy', Path('/unused'), pin)

    def test_draft_discovery_uses_release_id_after_eventual_visibility(self):
        draft=dict(id=123,tag_name='fixture',draft=True)
        with patch.object(prepare,'api',side_effect=[[],[draft],draft]) as api,patch.object(prepare.time,'sleep'):
            self.assertEqual(prepare.find_release('fixture'),draft)
        self.assertTrue(api.call_args_list[-1].args[0].endswith('/releases/123'))
        self.assertTrue(all('/releases/tags/' not in call.args[0] for call in api.call_args_list))

    def test_duplicate_release_rejected(self):
        draft=dict(id=123,tag_name='fixture',draft=True)
        with patch.object(prepare,'api',return_value=[draft,draft]):
            with self.assertRaisesRegex(ValueError,'Duplicate'):prepare.find_release('fixture')
