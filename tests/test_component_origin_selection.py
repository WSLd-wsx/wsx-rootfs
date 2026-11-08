"""Component selection must use an unambiguous published run receipt."""
import importlib.util
import json
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('select_origin',Path(__file__).resolve().parents[1]/'scripts/select-component-origin.py')
module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)


class ComponentSelection(unittest.TestCase):
    def test_only_matching_profile_and_exact_run_are_selected(self):
        prefix='build\tUpload and verify paired private GHCR package\t2026-11-08T11:00:00Z '
        log=('build\tBuild pinned private source closure\t2026-11-08T11:00:00Z   PROFILE: omarchy\n'
             +prefix+'```json\n'+prefix+json.dumps({'run_id':42,'transport':'ghcr'})+'\n'+prefix+'```\n')
        self.assertEqual(module.pin_from_log(log,'omarchy',42),{'run_id':42,'transport':'ghcr'})
        archived=log.replace('Upload and verify paired private GHCR package','UNKNOWN STEP')
        self.assertEqual(module.pin_from_log(archived,'omarchy',42),{'run_id':42,'transport':'ghcr'})
        self.assertIsNone(module.pin_from_log(log,'cachyos-plasma',42))
        with self.assertRaisesRegex(ValueError,'Missing or ambiguous'):
            module.pin_from_log(log,'omarchy',43)


if __name__ == '__main__': unittest.main()
