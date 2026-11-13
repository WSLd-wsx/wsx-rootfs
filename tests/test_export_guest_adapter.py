import importlib.util
import json
import runpy
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('export_adapter', ROOT/'scripts/export-guest-adapter.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ExportTests(unittest.TestCase):
    def test_generated_plasma_session_and_entry_bind_to_bundle(self):
        generator = runpy.run_path(str(ROOT/'scripts/stage-cachyos.py'))
        for name, generate in [('desktop.py', generator['session_source']), ('wsx-guest.py', generator['guest_source'])]:
            transformed = module.transform(name, generate())
            self.assertIn("Path(__file__).resolve()", transformed)
            if name == 'desktop.py':
                self.assertIn("deployment = Path('/usr/lib/wsx/runtime')", transformed)
                self.assertIn("root = Path('/usr/lib/wsx/runtime') if root is None", transformed)

    def staged_image(self, root):
        files = {
            'usr/lib/wsx/guest-protocol.py': 'protocol.py',
            'usr/lib/wsx/protocol-display.py': 'protocol-display.py',
            'usr/lib/wsx/protocol-retirement.py': 'protocol-retirement.py',
            'usr/lib/wsx/device-view.py': 'device-view.py',
            'usr/bin/wsx-guest': 'wsx-guest.py',
        }
        for target, source in files.items():
            path = root/target
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((ROOT/'guest'/source).read_bytes())
        desktop = root/'usr/lib/wsx/runtime/desktop.py'
        desktop.parent.mkdir(parents=True, exist_ok=True)
        desktop.write_text("from pathlib import Path\nimport runpy\nroot = Path(__file__).resolve().parent if root is None else Path(root).resolve()\ndeployment = Path(__file__).resolve().parent\nrunpy.run_path('/usr/lib/wsx/device-view.py')\n")
        (root/'usr/lib/wsx/guest-profile.json').write_text(json.dumps({'schema_version': 1, 'implementation': 'hyprland'}))

    def test_real_guest_sources_are_bound_to_the_same_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)/'image'; root.mkdir(); self.staged_image(root)
            output = Path(tmp)/'adapter'
            receipt = module.export(root, output, 'hyprland')
            self.assertFalse(receipt['admitted'])
            self.assertEqual(set(p.name for p in output.iterdir()), set(module.SOURCES))
            guest = (output/'wsx-guest.py').read_text()
            self.assertIn("str(Path(__file__).resolve()),'session'", guest)
            self.assertIn("Path(__file__).resolve().with_name('desktop.py')", guest)
            self.assertIn("deployment = Path('/usr/lib/wsx/runtime')", (output/'desktop.py').read_text())
            self.assertIn("root = Path('/usr/lib/wsx/runtime') if root is None", (output/'desktop.py').read_text())
            with self.assertRaises(ValueError): module.export(root, Path(tmp)/'wrong', 'plasma')

    def test_drift_does_not_publish_partial_adapter(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)/'image'; root.mkdir(); self.staged_image(root)
            path = root/'usr/bin/wsx-guest'
            path.write_text(path.read_text().replace('/usr/lib/wsx/device-view.py', '/different'))
            output = Path(tmp)/'adapter'
            with self.assertRaisesRegex(ValueError, 'Unexpected adapter source'):
                module.export(root, output, 'hyprland')
            self.assertFalse(output.exists())


if __name__ == '__main__': unittest.main()
