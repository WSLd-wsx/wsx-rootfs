# Original WSX code, PolyForm-Noncommercial-1.0.0. See LICENSE-MAP.md.
import base64
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import uuid

spec = importlib.util.spec_from_file_location('adapter_store', Path(__file__).resolve().parents[1] / 'guest/adapter-store.py')
store = importlib.util.module_from_spec(spec)
spec.loader.exec_module(store)


def sample():
    payload = {name: ('fixture ' + name).encode() for name in store.FILES}
    manifest = {'schema_version': 1, 'kind': 'wsx-guest-adapter', 'protocol_major': 2,
                'implementation': 'hyprland', 'files': {name: {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)} for name, data in payload.items()}}
    raw = json.dumps(manifest, sort_keys=True).encode()
    return raw, hashlib.sha256(raw).hexdigest(), {name: base64.b64encode(data).decode() for name, data in payload.items()}


class AdapterStoreTests(unittest.TestCase):
    def test_stage_reuse_and_detect_corruption(self):
        raw, pin, files = sample()
        with tempfile.TemporaryDirectory() as root:
            self.assertTrue(store.stage(root, raw, pin, files)['staged'])
            self.assertFalse(store.stage(root, raw, pin, files)['staged'])
            (Path(root)/pin/'desktop.py').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'differs'):
                store.stage(root, raw, pin, files)

    def test_concurrent_staging_has_one_winner(self):
        raw, pin, files = sample()
        with tempfile.TemporaryDirectory() as root:
            with ThreadPoolExecutor(max_workers=4) as workers:
                results = list(workers.map(lambda _: store.stage(root, raw, pin, files), range(4)))
            self.assertEqual(sum(result['staged'] for result in results), 1)
            self.assertEqual(store.verify(Path(root)/pin, pin)['implementation'], 'hyprland')

    def test_failed_commit_preserves_existing_and_cleans_own_temporary(self):
        raw, pin, files = sample()
        with tempfile.TemporaryDirectory() as root:
            with patch.object(store.os, 'rename', side_effect=OSError('injected')):
                with self.assertRaisesRegex(OSError, 'injected'):
                    store.stage(root, raw, pin, files)
            self.assertFalse((Path(root)/pin).exists())
            self.assertEqual([p.name for p in Path(root).iterdir()], ['.lock'])

    def test_new_selection_does_not_change_existing_session_pin(self):
        raw, first, files = sample()
        with tempfile.TemporaryDirectory() as root:
            store.stage(root, raw, first, files)
            store.select(root, first, 'hyprland')
            first_session = uuid.uuid4()
            self.assertEqual(store.pin_session(root, first_session, 'hyprland')['sha256'], first)
            changed = json.loads(raw)
            data = b'new desktop'
            changed['files']['desktop.py'] = {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
            second_raw = json.dumps(changed, sort_keys=True).encode()
            second = hashlib.sha256(second_raw).hexdigest()
            newer_files = dict(files, **{'desktop.py': base64.b64encode(data).decode()})
            store.stage(root, second_raw, second, newer_files)
            store.select(root, second, 'hyprland')
            self.assertEqual(store.session_pin(root, first_session, 'hyprland')['sha256'], first)
            self.assertEqual(store.pin_session(root, uuid.uuid4(), 'hyprland')['sha256'], second)
            pin = json.loads((Path(root)/('session-'+first_session.hex+'.json')).read_text())
            self.assertEqual(pin['sha256'], first)
            with self.assertRaises(FileExistsError): store.pin_session(root, first_session, 'hyprland')
            with self.assertRaisesRegex(ValueError, 'implementation mismatch'): store.select(root, second, 'plasma')
            self.assertEqual(store._selection(Path(root)), second)

    def test_pin_publish_failure_does_not_leave_partial_pin(self):
        raw, pin, files = sample()
        with tempfile.TemporaryDirectory() as root:
            store.stage(root, raw, pin, files)
            store.select(root, pin, 'hyprland')
            instance = uuid.uuid4()
            with patch.object(store.os, 'link', side_effect=OSError('injected')):
                with self.assertRaisesRegex(OSError, 'injected'):
                    store.pin_session(root, instance, 'hyprland')
            self.assertFalse((Path(root)/('session-'+instance.hex+'.json')).exists())
            self.assertFalse(any(p.name.startswith('.session-') for p in Path(root).iterdir()))

    def test_selection_rejects_tampering_before_switch(self):
        raw, pin, files = sample()
        with tempfile.TemporaryDirectory() as root:
            store.stage(root, raw, pin, files)
            (Path(root)/pin/'desktop.py').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'differs'): store.select(root, pin, 'hyprland')
            self.assertFalse((Path(root)/'active.json').exists())

    def test_rejects_bad_pin_and_tampering_without_staging(self):
        raw, pin, files = sample()
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaisesRegex(ValueError, 'digest'):
                store.stage(root, raw, '0'*64, files)
            files['desktop.py'] = base64.b64encode(b'wrong').decode()
            with self.assertRaisesRegex(ValueError, 'differs'):
                store.stage(root, raw, pin, files)
            self.assertFalse((Path(root)/pin).exists())

    def test_rejects_symlink_lock_and_extra_files(self):
        raw, pin, files = sample()
        with tempfile.TemporaryDirectory() as root:
            (Path(root)/'.lock').symlink_to('/dev/null')
            with self.assertRaises(OSError): store.stage(root, raw, pin, files)
        with tempfile.TemporaryDirectory() as root:
            files['extra'] = 'eA=='
            with self.assertRaisesRegex(ValueError, 'Incomplete'):
                store.stage(root, raw, pin, files)

    def test_rejects_duplicate_keys_and_boolean_schema(self):
        for raw in (b'{"schema_version":1,"schema_version":1}', b'{"schema_version":true,"kind":"wsx-guest-adapter","protocol_major":2,"implementation":"hyprland","files":{}}'):
            with self.assertRaises(ValueError): store._manifest(raw, hashlib.sha256(raw).hexdigest())


if __name__ == '__main__': unittest.main()
