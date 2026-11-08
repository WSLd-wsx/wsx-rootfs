"""Workflow-selected inputs stay profile-scoped and reject unsafe origins."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import workflow_component_inputs as inputs


class WorkflowInputs(unittest.TestCase):
    def test_selection_updates_only_the_selected_profile(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); (root/'components').mkdir()
            (root/'components/reuse.json').write_text(json.dumps({'schema_version':1,'profiles':{'omarchy':None,'cachyos-plasma':'old'}}))
            (root/'components/source-delivery.json').write_text(json.dumps({'schema_version':1,'mode':'shared-v2','profiles':{'omarchy':None,'cachyos-plasma':'old'},'component_origins':{'omarchy':None,'cachyos-plasma':'old'}}))
            pin = {'transport':'ghcr','image':inputs.component_registry.OPS_IMAGE+'@sha256:'+'a'*64,
                   'run_id':1,'source_commit':'b'*40,'manifest_sha256':'c'*64,
                   'run_repository':'WSLd-wsx/wsx-rootfs-ops','workflow_commit':'d'*40}
            source = {'tag':'graphics-sources-omarchy-'+'e'*20,'manifest_sha256':'f'*64}
            inputs.apply(root, 'omarchy', {'component':pin,'shared_source':source}, verify=False)
            self.assertEqual(json.loads((root/'components/reuse.json').read_text())['profiles']['omarchy'],pin)
            delivery = json.loads((root/'components/source-delivery.json').read_text())
            self.assertEqual(delivery['profiles']['omarchy'],source)
            self.assertEqual(delivery['profiles']['cachyos-plasma'],'old')
            pin['image'] = 'ghcr.io/other/package@sha256:'+'a'*64
            with self.assertRaises(ValueError):
                inputs.apply(root, 'omarchy', {'component':pin,'shared_source':source}, verify=False)


if __name__ == '__main__':
    unittest.main()
