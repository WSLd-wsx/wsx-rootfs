# Original WSX code, PolyForm-Noncommercial-1.0.0. See LICENSE-MAP.md.
import importlib.util
import json
import tempfile
from pathlib import Path
import unittest
import uuid
from test_adapter_store import sample, store

spec = importlib.util.spec_from_file_location('bootstrap', Path(__file__).resolve().parents[1]/'guest/bootstrap-v2.py')
bootstrap = importlib.util.module_from_spec(spec); spec.loader.exec_module(bootstrap)

class BootstrapTests(unittest.TestCase):
    def test_profile_checked_selection_and_pinning(self):
        raw, pin, files = sample()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            profile = root/'profile.json'
            profile.write_text(json.dumps({'schema_version': 1, 'implementation': 'hyprland'}))
            helpers = {name: getattr(store, name) for name in ('stage', 'verify', '_read_regular', 'select', 'pin_session', 'session_pin')}
            def request(op, params):
                return bootstrap.handle(dict(protocol=bootstrap.PROTOCOL, major=2, id='test-2', operation=op, params=params), root, helpers, profile)
            self.assertTrue(request('adapter.stage', dict(manifest=raw.decode(), expected_sha256=pin, files=files))['ok'])
            self.assertTrue(request('adapter.select', {'sha256': pin})['ok'])
            instance = str(uuid.uuid4())
            self.assertFalse(request('session.pin', {'instance': instance, 'sha256': '0'*64})['ok'])
            self.assertEqual(request('session.pin', {'instance': instance, 'sha256': pin})['result']['sha256'], pin)
            self.assertEqual(request('session.inspect', {'instance': instance})['result']['sha256'], pin)
            self.assertFalse(request('session.pin', {'instance': instance, 'sha256': pin})['ok'])
            profile.write_text(json.dumps({'schema_version': 1, 'implementation': 'plasma'}))
            self.assertFalse(request('session.inspect', {'instance': instance})['ok'])
            self.assertFalse(request('adapter.select', {'sha256': pin})['ok'])

    def test_stages_and_inspects_without_activation(self):
        raw, pin, files = sample()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            def request(op, params):
                return bootstrap.handle(dict(protocol=bootstrap.PROTOCOL,major=2,id='test-1',operation=op,params=params), root,
                                        {'stage':store.stage,'verify':store.verify})
            self.assertFalse(request('capabilities', {})['result']['activation_supported'])
            self.assertTrue(request('adapter.stage', dict(manifest=raw.decode(),expected_sha256=pin,files=files))['ok'])
            inspected = request('adapter.inspect', dict(sha256=pin))['result']
            self.assertTrue(inspected['integrity_verified'])
            self.assertFalse(inspected['publisher_verified'])
            self.assertFalse(inspected['activation_supported'])
            self.assertNotIn('active', inspected)
            self.assertFalse(request('adapter.activate', dict(sha256=pin))['ok'])
            self.assertFalse(request('execute', {'command':'id'})['ok'])
            self.assertFalse(request('adapter.inspect', dict(sha256='../etc'))['ok'])
            malformed = request('capabilities', {}); malformed['id'] = 'x' * 1000
            self.assertIsNone(bootstrap.handle(malformed, root, {'stage':store.stage,'verify':store.verify})['id'])

if __name__ == '__main__': unittest.main()
