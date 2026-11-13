# Original WSX code, PolyForm-Noncommercial-1.0.0. See LICENSE-MAP.md.
import importlib.util
import base64
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path
import unittest
import uuid
from test_adapter_store import sample, store

spec = importlib.util.spec_from_file_location('bootstrap', Path(__file__).resolve().parents[1]/'guest/bootstrap-v2.py')
bootstrap = importlib.util.module_from_spec(spec); spec.loader.exec_module(bootstrap)

class BootstrapTests(unittest.TestCase):
    def test_dispatch_executes_old_session_after_selection_changes(self):
        raw, first, encoded = sample()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            profile = root/'profile.json'
            profile.write_text(json.dumps({'schema_version': 1, 'implementation': 'hyprland'}))
            def stage_version(tag):
                manifest = json.loads(raw)
                script = ('import sys\nprint(' + repr(tag) + ')\nprint(sys.argv[1])\n').encode()
                manifest['files']['wsx-guest.py'] = {'sha256': hashlib.sha256(script).hexdigest(), 'bytes': len(script)}
                data = json.dumps(manifest, sort_keys=True).encode()
                identity = hashlib.sha256(data).hexdigest()
                payload = dict(encoded, **{'wsx-guest.py': base64.b64encode(script).decode()})
                store.stage(root, data, identity, payload)
                store.select(root, identity, 'hyprland')
                return identity
            old = stage_version('old')
            old_instance = str(uuid.uuid4())
            store.pin_session(root, old_instance, 'hyprland', old)
            new = stage_version('new')
            new_instance = str(uuid.uuid4())
            store.pin_session(root, new_instance, 'hyprland', new)
            helpers = {'_read_regular': store._read_regular, 'session_pin': store.session_pin}
            for instance, expected in ((old_instance, 'old'), (new_instance, 'new')):
                command = bootstrap.dispatch(root, helpers, profile, 'start', instance)
                output = subprocess.run(command, capture_output=True, text=True, check=True).stdout.splitlines()
                self.assertEqual(output, [expected, 'start'])

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
            args = bootstrap.dispatch(root, helpers, profile, 'start', instance)
            self.assertEqual(args, ['/usr/bin/python3', '-I', str(root/pin/'wsx-guest.py'), 'start', '--instance', instance])
            self.assertEqual(bootstrap.dispatch(root, helpers, profile, 'host-call', instance)[-1], 'host-call')
            with self.assertRaisesRegex(ValueError, 'Unsupported'):
                bootstrap.dispatch(root, helpers, profile, 'execute', instance)
            with self.assertRaises(FileNotFoundError):
                bootstrap.dispatch(root, helpers, profile, 'start', str(uuid.uuid4()))
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
            self.assertTrue(request('capabilities', {})['result']['activation_supported'])
            self.assertTrue(request('capabilities', {})['result']['dispatch_supported'])
            self.assertTrue(request('adapter.stage', dict(manifest=raw.decode(),expected_sha256=pin,files=files))['ok'])
            inspected = request('adapter.inspect', dict(sha256=pin))['result']
            self.assertTrue(inspected['integrity_verified'])
            self.assertFalse(inspected['publisher_verified'])
            self.assertNotIn('active', inspected)
            self.assertFalse(request('adapter.activate', dict(sha256=pin))['ok'])
            self.assertFalse(request('execute', {'command':'id'})['ok'])
            self.assertFalse(request('adapter.inspect', dict(sha256='../etc'))['ok'])
            malformed = request('capabilities', {}); malformed['id'] = 'x' * 1000
            self.assertIsNone(bootstrap.handle(malformed, root, {'stage':store.stage,'verify':store.verify})['id'])

if __name__ == '__main__': unittest.main()
