"""Retirement races without a real session or GPU."""
import importlib.util
from pathlib import Path
import subprocess
import unittest
import uuid
import tempfile
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('retirement',Path(__file__).resolve().parents[1]/'guest/protocol-retirement.py')
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
class DrainTests(unittest.TestCase):
    def test_only_wholly_owned_user_units_are_selected(self):
        instance=uuid.uuid4()
        group='/user.slice/user-1000.slice/user@1000.service/app.slice/dconf.service'
        with tempfile.TemporaryDirectory() as root:
            proc=Path(root)
            def add(pid,tagged):
                p=proc/str(pid);p.mkdir()
                (p/'cgroup').write_text('0::'+group)
                (p/'environ').write_bytes(('WSX_DESKTOP_INSTANCE='+str(instance)).encode()+b'\0' if tagged else b'OTHER=1\0')
            add(42,True)
            units=r.owned_user_units(instance,proc)
            self.assertEqual([(u[0],u[1]) for u in units],[(1000,'dconf.service')])
            add(43,False)
            with self.assertRaisesRegex(RuntimeError,'another session'):
                r.owned_user_units(instance,proc)
    def test_user_manager_and_other_instances_are_never_stop_targets(self):
        instance=uuid.uuid4()
        with tempfile.TemporaryDirectory() as root:
            proc=Path(root)
            for pid,group,owner in [(1,'/user.slice/user-1000.slice/user@1000.service',instance),
                                    (2,'/user.slice/user-1000.slice/user@1000.service/app.slice/app.service',uuid.uuid4())]:
                p=proc/str(pid);p.mkdir();(p/'cgroup').write_text('0::'+group)
                (p/'environ').write_bytes(('WSX_DESKTOP_INSTANCE='+str(owner)).encode()+b'\0')
            self.assertEqual(r.owned_user_units(instance,proc),[])
    def test_asynchronous_process_exit_is_waited_without_kill(self):
        with patch.object(r,'instance_processes',side_effect=[[{'pid':42}],[]]),patch.object(r.Path,'exists',return_value=False),patch.object(r.time,'sleep') as sleep:
            r.wait_session_drain(uuid.uuid4())
            sleep.assert_called_once()
    def test_timeout_reports_remaining_process_and_retains_ownership(self):
        with patch.object(r,'instance_processes',return_value=[{'pid':42,'name':'held'}]),patch.object(r.Path,'exists',return_value=False):
            with self.assertRaisesRegex(RuntimeError,'"pid": 42'):r.wait_session_drain(uuid.uuid4(),timeout=0)
    def test_seat_or_owner_never_implies_success(self):
        with patch.object(r,'instance_processes',return_value=[]),patch.object(r.Path,'exists',return_value=True):
            with self.assertRaises(RuntimeError):r.wait_session_drain(uuid.uuid4(),timeout=0)
    def test_disappeared_unit_reconciles_only_with_inactive_state(self):
        for state in ('inactive','active','failed'):
            results=[subprocess.CompletedProcess([],5),subprocess.CompletedProcess([],0,stdout=state)]
            with patch.object(r.subprocess,'run',side_effect=results):
                if state in ('inactive','failed'):r.stop_unit('test.service')
                else:
                    with self.assertRaises(RuntimeError):r.stop_unit('test.service')
