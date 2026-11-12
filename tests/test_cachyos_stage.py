"""Exercise negotiated Plasma graphics selection with isolated fixture files."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import sys
from types import SimpleNamespace
import unittest
import uuid
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('stage_cachyos', ROOT/'scripts/stage-cachyos.py')
stage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage)


def fixture(directory, files, **metadata):
    hashes = {}
    for name in files:
        path = directory/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'fixture')
        hashes[name] = hashlib.sha256(b'fixture').hexdigest()
    (directory/'manifest.json').write_text(json.dumps(dict(files=hashes, **metadata)))


class PlasmaStageTests(unittest.TestCase):
    def test_linear_pins_kwin_without_opaque_flags_and_rejects_corruption(self):
        namespace = {'__name__': 'fixture', '__file__': '/tmp/desktop.py'}
        exec(stage.session_source(), namespace)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture(root/'mesa', ['lib/libgbm.so.1','lib/libEGL_mesa.so.0',
                'lib/libGLX_mesa.so.0','lib/libgallium-26.1.8.so',
                'share/glvnd/egl_vendor.d/50_mesa.json'], version='26.1.8',
                opaque_consumer=True, opaque_gbm_export=True, linear_shared_compat=True)
            fixture(root/'venus', ['libvulkan_virtio.so', 'virtio_icd.json'], version='26.2.4',
                zink_drm_identity=True, opaque_wsi=True, opaque_import=True, direct_wsi='linear-v1')
            fixture(root/'kwin-opaque', ['bin/kwin_wayland', 'lib/libkwin.so.6'], abi=2)
            with patch.dict(os.environ, {'WSX_SHARING_PATH': 'linear-v1'}):
                env = namespace['mesa_environment'](root)
                self.assertEqual(env['WSX_VENUS_DIRECT_WSI'], 'linear-v1')
                self.assertEqual(env['VN_PERF'], 'no_async_mem_alloc')
                self.assertNotIn('WSX_OPAQUE_COMPOSITOR', env)
                self.assertTrue(env['PATH'].startswith(str(root/'kwin-opaque/bin')))
                (root/'kwin-opaque/bin/kwin_wayland').write_bytes(b'corrupt')
                with self.assertRaisesRegex(RuntimeError, 'hash mismatch'):
                    namespace['mesa_environment'](root)

    def test_session_parameters_are_not_a_baked_deployment(self):
        session = stage.session_source()
        self.assertTrue(session.startswith('# SPDX-License-Identifier: MIT\n'))
        self.assertIn('# Adapted by the WSX rootfs staging recipe from vendor/wsx-proto/device-host/production/start-cachyos-plasma.py.\n', session)
        self.assertNotIn("deployment.parent / 'wsx-runtime.json'", session)
        self.assertIn("instance.hex + '.json'", session)
        self.assertLess(session.index("env['PULSE_SERVER']"), session.index('    configure_plasma_service(account, env)'))
        self.assertIn("os.environ['WSX_LOCALE']", session)

    def test_staging_records_exact_package_versions(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            root = work/'root'
            (root/'usr/bin').mkdir(parents=True)
            (root/'usr/lib').mkdir(parents=True)
            helper = root/'usr/lib/plasma-setup-xwayland'
            helper.write_text('fixture')
            helper.chmod(0o755)
            components = work/'private'
            for name in ('mesa', 'venus', 'kwin-opaque'):
                (components/name).mkdir(parents=True)
                (components/name/'manifest.json').write_text(json.dumps({'version':'fixture','files':{'fixture':'a'*64}}))
            (work/'rootfs-packages.txt').write_text('kwin 6.8.1-2\nplasma-workspace 6.8.1-1\nqt6-base 6.12.0-3\n')
            with patch.object(sys, 'argv', ['stage', str(root), str(components)]), patch.object(stage.subprocess, 'run'):
                stage.main()
            self.assertTrue((root/'usr/lib/wsx/guest-protocol.py').is_file())
            profile = json.loads((root/'usr/lib/wsx/guest-profile.json').read_text())
            self.assertEqual(profile['implementation'], 'plasma')
            self.assertEqual(set(profile['component_manifests']), {'mesa','venus','kwin-opaque'})
            lock = json.loads((root/'usr/lib/wsx/plasma-compat.json').read_text())
            self.assertEqual(lock['cpu_architecture_level'], 'x86-64-v3')
            self.assertEqual(lock['packages']['kwin'], '6.8.1-2')
            self.assertEqual(str((root/'opt/wsx/kwin-opaque-6.8.1/lib/libexec/plasma-setup-xwayland').readlink()), '/usr/lib/plasma-setup-xwayland')

    def test_cpu_and_plasma_version_are_admitted_before_session(self):
        namespace = {'__name__': 'fixture', '__file__': '/tmp/wsx-guest.py'}
        exec(stage.guest_source(), namespace)
        check = namespace['check_plasma_compatibility']
        flags = 'flags : cx16 lahf_lm pni popcnt sse4_1 sse4_2 ssse3 avx avx2 bmi1 bmi2 f16c fma abm movbe xsave'
        versions = {'kwin':'6.8.1-2', 'plasma-workspace':'6.8.1-1', 'qt6-base':'6.12.0-3'}
        check(flags, versions, versions)
        with self.assertRaisesRegex(ValueError, 'x86-64-v3'):
            check(flags.replace('avx2', ''), versions, versions)
        with self.assertRaisesRegex(ValueError, 'version mismatch'):
            check(flags, dict(versions, kwin='6.8.1-3'), versions)

    def test_first_user_initialization_populates_official_keyrings(self):
        namespace = {'__name__': 'fixture', '__file__': '/tmp/wsx-guest.py'}
        exec(stage.guest_source(), namespace)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'etc').mkdir()
            namespace['STATE'] = root/'state/initialized.json'
            namespace['STATE'].parent.mkdir()
            real_path = Path
            def redirected(value):
                value = str(value)
                return root/value.lstrip('/') if value.startswith('/etc/') else real_path(value)
            namespace['Path'] = redirected
            account = SimpleNamespace(pw_uid=1234, pw_gid=1234, pw_dir=str(root/'home'))
            calls = []
            def fake_run(argv, **kwargs):
                calls.append((argv, kwargs))
            namespace['run'] = fake_run
            namespace['pwd'] = SimpleNamespace(getpwnam=unittest.mock.Mock(side_effect=[KeyError, account, account]))
            namespace['getpass'] = SimpleNamespace(getpass=lambda prompt: 'fixture-password')
            args = SimpleNamespace(user='wsx_fixture', locale='C.UTF-8', timezone='UTC', password_stdin=False)
            namespace['initialize'](args)
            commands = [entry[0] for entry in calls]
            self.assertIn(['/usr/bin/pacman-key', '--init'], commands)
            self.assertIn(['/usr/bin/pacman-key', '--populate', 'archlinux', 'cachyos'], commands)
            self.assertIn(['/usr/bin/loginctl', 'enable-linger', 'wsx_fixture'], commands)
            self.assertFalse(any('fixture-password' in str(command) for command in commands))
            state = json.loads((root/'state/initialized.json').read_text())
            self.assertEqual(state['user'], 'wsx_fixture')
            self.assertNotIn('fixture-password', json.dumps(state))

    def test_guest_uses_mixed_kill_and_instance_input(self):
        guest = stage.guest_source()
        session = stage.session_source()
        self.assertIn('KillMode=process', guest)
        self.assertIn('TimeoutStopSec=45', guest)
        self.assertIn("['/usr/bin/pacman-key', '--init']", guest)
        self.assertIn("['/usr/bin/pacman-key', '--populate', 'archlinux', 'cachyos']", guest)
        self.assertIn("str(profile['input_port'])", session)
        self.assertNotIn("pwd.getpwnam('wsx')", session)
        self.assertIn('Opaque kernel ABI unavailable', session)

    def test_logout_falls_back_to_exact_process_identity(self):
        namespace = {'__name__': 'fixture', '__file__': '/tmp/desktop.py'}
        exec(stage.session_source(), namespace)
        account = SimpleNamespace(pw_name='fixture', pw_uid=1234)
        instance = '48d252cc-9e97-4b69-9bbc-1c7ab52145ac'
        calls = []
        def systemctl(argv, **kwargs):
            return SimpleNamespace(stdout='123\n' if 'MainPID' in argv[-2] else '', returncode=0)
        class ProcessPath:
            def __init__(self, value): self.value = str(value)
            def __truediv__(self, value): return ProcessPath(self.value+'/'+value)
            def read_bytes(self): return ('WSX_DESKTOP_INSTANCE='+instance+'\0').encode()
        namespace['subprocess'] = SimpleNamespace(run=systemctl)
        namespace['run'] = lambda argv: calls.append(argv)
        namespace['Path'] = ProcessPath
        with patch.object(namespace['os'].path, 'samefile', return_value=True):
            namespace['request_plasma_logout'](account, instance)
        self.assertEqual(len(calls), 1)
        with patch.object(namespace['os'].path, 'samefile', return_value=False):
            with self.assertRaisesRegex(RuntimeError, 'different desktop instance'):
                namespace['request_plasma_logout'](account, instance)

    def test_lifecycle_preserves_failed_owner_and_rejects_retained_seat(self):
        guest = stage.guest_source()
        session = stage.session_source()
        self.assertIn("state.stdout.strip() != 'inactive'", guest)
        self.assertIn('Retained seat socket requires ownership diagnosis', guest)
        self.assertIn('Retained session ownership record requires diagnosis', guest)
        self.assertIn("'--property=KillMode=process'", guest)
        self.assertNotIn('atexit.register(stop_input)', session)
        self.assertLess(session.index('    wait_plasma_stopped(account)\n    stop_input()'),
                        session.index('    if seat.poll() is not None:'))

    def test_owner_record_tracks_process_birth_and_excludes_replacement(self):
        namespace = {'__name__': 'fixture', '__file__': '/tmp/desktop.py'}
        exec(stage.session_source(), namespace)
        account = SimpleNamespace(pw_uid=1234)
        instance = uuid.uuid4()
        with tempfile.TemporaryDirectory() as tmp:
            path, fd, record = namespace['create_owner_record'](instance, account, Path(tmp))
            try:
                namespace['record_child'](fd, record, 'input', SimpleNamespace(pid=os.getpid()))
                saved = json.loads(path.read_text())
                self.assertEqual(saved['uid'], 1234)
                self.assertEqual(saved['instance_id'], str(instance))
                self.assertEqual(saved['children']['input']['start_time'], namespace['process_start_time'](os.getpid()))
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)
                with self.assertRaises(FileExistsError):
                    namespace['create_owner_record'](instance, account, Path(tmp))
                path.unlink()
                path.write_text('different owner')
                with self.assertRaisesRegex(RuntimeError, 'Owner record changed'):
                    namespace['retire_owner_record'](path, fd)
            finally:
                os.close(fd)

    def test_session_start_fails_closed_for_retained_state(self):
        namespace = {'__name__': 'fixture', '__file__': '/tmp/wsx-guest.py'}
        exec(stage.guest_source(), namespace)
        instance = uuid.uuid4()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'run/wsx').mkdir(parents=True)
            real_path = Path
            namespace['Path'] = lambda value: root/str(value).lstrip('/') if str(value).startswith('/run/') else real_path(value)
            namespace['read_spec'] = lambda value: {'user': 'fixture'}
            state = {'active': 'inactive', 'linger': 'yes'}
            namespace['subprocess'] = SimpleNamespace(run=lambda argv, **kwargs: SimpleNamespace(
                stdout=state['linger'] if 'show-user' in argv else state['active']))
            calls = []
            namespace['run'] = lambda argv, **kwargs: calls.append(argv)
            with patch.object(namespace['os'], 'geteuid', return_value=0), \
                 patch.object(sys, 'argv', ['wsx-guest', 'start', '--instance', str(instance)]):
                state['active'] = 'failed'
                with self.assertRaisesRegex(ValueError, 'not safely retired'):
                    namespace['main']()
                state['active'] = 'inactive'
                owner = root/'run/wsx'/f'{instance.hex}.owner.json'
                owner.write_text('{}')
                with self.assertRaisesRegex(ValueError, 'ownership record'):
                    namespace['main']()
                owner.unlink()
                state['linger'] = 'no'
                with self.assertRaisesRegex(ValueError, 'lifetime is not enabled'):
                    namespace['main']()
                state['linger'] = 'yes'
                namespace['main']()
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0][0], 'systemd-run')
