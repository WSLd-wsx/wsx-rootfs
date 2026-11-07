"""Package declaration checks with inert files, not runtime acceptance."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('desktop_contract', ROOT/'scripts/desktop_contract.py')
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)


class DeclarationTests(unittest.TestCase):
    def fixture(self, root):
        guest = root/'rootfs/usr/lib/wsx'; guest.mkdir(parents=True)
        for name in module.FILES:
            (guest/name).write_bytes(b'fixture'); (guest/name).chmod(0o644)
        (guest/'guest-protocol.py').write_text('CAPABILITIES = '+repr(module.CAPABILITIES)+'\n')
        (guest/'runtime').mkdir()
        for name in ('desktop.py','wsx-input-guest'):
            path=guest/'runtime'/name;path.write_bytes(b'fixture');path.chmod(0o755)
        manifests = {}
        for name in ('mesa','venus','opaque-consumer'):
            path = guest/'runtime'/name/'manifest.json';path.parent.mkdir(parents=True)
            path.write_text('{}');manifests[name]=hashlib.sha256(path.read_bytes()).hexdigest()
        (guest/'guest-profile.json').write_text(json.dumps(dict(schema_version=1,implementation='hyprland',
            consumer='opaque-consumer',component_manifests=manifests)))
        native = root/'wsx-native-host.exe'; native.write_bytes(b'inert-test-file')
        files = {native.name:dict(bytes=native.stat().st_size, sha256=hashlib.sha256(native.read_bytes()).hexdigest())}
        receipt = root/'verified-files.json'; receipt.write_text(json.dumps(files))
        self.pin_receipt(root)
        return root/'rootfs', receipt

    def pin_receipt(self, root):
        (root/'contract.json').write_text(json.dumps(dict(module.EXPECTED,minimum_wsx_core_version='0.2.1',
            runtime_receipt_sha256=hashlib.sha256((root/'verified-files.json').read_bytes()).hexdigest())))

    def test_default_build_always_declares_protocol_and_binds_guest_profile(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(module,'PIN_DIR',Path(tmp)):
            rootfs, receipt = self.fixture(Path(tmp))
            value = module.declaration(rootfs)
            self.assertIn('graphics.distro-device-view-v1',value['required_capabilities'])
            self.assertIn('graphics.distro-input-view-v1',value['required_capabilities'])
            self.assertEqual(value['runtime_receipt_sha256'], hashlib.sha256(receipt.read_bytes()).hexdigest())
            self.assertEqual(value['guest_profile_sha256'], hashlib.sha256((rootfs/'usr/lib/wsx/guest-profile.json').read_bytes()).hexdigest())
            self.assertNotIn('validation', value)
            (rootfs/'usr/lib/wsx/runtime/mesa/manifest.json').write_text('{"changed":true}')
            with self.assertRaisesRegex(ValueError,'profile mismatch'): module.declaration(rootfs)

    def test_optional_local_runtime_verification_does_not_allow_pair_override(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(module,'PIN_DIR',Path(tmp)):
            rootfs, receipt = self.fixture(Path(tmp))
            module.declaration(rootfs,receipt,'0.2.1')
            with self.assertRaises(ValueError): module.declaration(rootfs,receipt,'0.2.0')
            (receipt.parent/'wsx-native-host.exe').write_bytes(b'tampered-test!!')
            with self.assertRaisesRegex(ValueError,'mismatch'): module.declaration(rootfs,receipt,'0.2.1')

    def test_missing_protocol_bad_pin_and_traversal_reject(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(module,'PIN_DIR',Path(tmp)):
            rootfs, receipt = self.fixture(Path(tmp))
            receipt.write_text(json.dumps({'wsx-native-host.exe':{},'../escape':{}}))
            with self.assertRaisesRegex(ValueError,'differs'): module.declaration(rootfs)
            receipt.write_text(json.dumps({'../escape':{},'wsx-native-host.exe':{}}));self.pin_receipt(Path(tmp))
            with self.assertRaisesRegex(ValueError,'Unsafe'): module.declaration(rootfs)
        with tempfile.TemporaryDirectory() as tmp, patch.object(module,'PIN_DIR',Path(tmp)):
            rootfs, receipt = self.fixture(Path(tmp))
            (rootfs/'usr/lib/wsx/protocol-display.py').unlink()
            with self.assertRaisesRegex(ValueError,'not packaged'): module.declaration(rootfs)

    def test_package_must_contain_both_isolation_capabilities_and_executable_input(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(module,'PIN_DIR',Path(tmp)):
            rootfs, receipt = self.fixture(Path(tmp))
            guest=rootfs/'usr/lib/wsx'
            (guest/'guest-protocol.py').write_text('CAPABILITIES = '+repr(module.CAPABILITIES[:-1])+'\n')
            with self.assertRaisesRegex(ValueError,'required capabilities'): module.declaration(rootfs)
            (guest/'guest-protocol.py').write_text('CAPABILITIES = '+repr(module.CAPABILITIES)+'\n')
            (guest/'runtime/wsx-input-guest').chmod(0o644)
            with self.assertRaisesRegex(ValueError,'not executable'): module.declaration(rootfs)


if __name__ == '__main__': unittest.main()
