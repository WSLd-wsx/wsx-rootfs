"""Offline rejection checks; no user, session, module or GPU operation is run."""
import importlib.util
import json
from pathlib import Path
import tempfile
import uuid
from types import SimpleNamespace
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('wsx_guest',Path(__file__).resolve().parents[1]/'guest/wsx-guest.py')
guest=importlib.util.module_from_spec(spec);spec.loader.exec_module(guest)


class GuestAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.state=Path(self.temp.name)/'initialized.json'
        mock=patch.object(guest,'STATE',self.state);mock.start();self.addCleanup(mock.stop)
        self.args=SimpleNamespace(user='wsx_fixture',locale='C.UTF-8',timezone='UTC',password_stdin=False)

    def test_root_and_injected_user_rejected_before_mutation(self):
        for name in ('root','bad\nname','../../root','a:b'):
            self.args.user=name
            with patch.object(guest,'run') as run, self.assertRaises(ValueError):
                guest.initialize(self.args)
            run.assert_not_called()

    def test_existing_user_not_taken_over(self):
        with patch.object(guest.pwd,'getpwnam',return_value=SimpleNamespace(pw_uid=1234)), \
             patch.object(guest,'run') as run, self.assertRaises(ValueError):
            guest.initialize(self.args)
        run.assert_not_called()

    def test_pending_user_uid_must_match(self):
        self.state.with_name('initialization-pending.json').write_text(json.dumps(dict(user='wsx_fixture',locale='C.UTF-8',timezone='UTC',created_uid=1234)))
        with patch.object(guest.pwd,'getpwnam',return_value=SimpleNamespace(pw_uid=5678)), \
             patch.object(guest,'run') as run, self.assertRaises(ValueError):
            guest.initialize(self.args)
        run.assert_not_called()

    def test_empty_password_never_creates_user(self):
        with patch.object(guest.pwd,'getpwnam',side_effect=KeyError), \
             patch.object(guest.getpass,'getpass',return_value=''), \
             patch.object(guest,'run') as run, self.assertRaises(ValueError):
            guest.initialize(self.args)
        run.assert_not_called()

    def test_reinitialize_does_not_reset_password(self):
        self.state.write_text('{}')
        with patch.object(guest,'run') as run, self.assertRaises(ValueError):
            guest.initialize(self.args)
        run.assert_not_called()

    def test_session_passes_negotiated_path_to_installed_desktop(self):
        instance=uuid.UUID('12345678-1234-4234-8234-123456789abc')
        for path in ('opaque-v1','linear-v1'):
            spec={'user':'fixture','locale':'C.UTF-8','sharing_path':path,'drm_node':'/dev/dri/card7'}
            with self.subTest(path=path), patch.object(guest.os,'geteuid',return_value=0), \
                 patch.object(guest.sys,'argv',['wsx-guest','session','--instance',str(instance)]), \
                 patch.object(guest,'read_spec',return_value=spec), patch.object(guest.os,'execve') as execute:
                guest.main()
                executable,argv,env=execute.call_args.args
                self.assertEqual(executable,'/usr/bin/python3')
                self.assertEqual(argv,['python3','-I',str(guest.RUNTIME/'desktop.py'),spec['drm_node'],str(instance)])
                self.assertEqual(env['WSX_SHARING_PATH'],path)
