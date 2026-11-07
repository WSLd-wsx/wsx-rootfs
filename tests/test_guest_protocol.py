"""Protocol conformance and mocked adapters; no desktop or device is started."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('protocol',ROOT/'guest/protocol.py')
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)


def request(operation='capabilities', params=None):
    return dict(protocol='wsx-guest',major=1,minor=0,id='conformance-1',operation=operation,params=params or {})


def display():
    return dict(signature='opaque-session-epoch',monitor=dict(name='output-a',width=1920,height=1080,scale=1.25),
                modes=[dict(width=1920,height=1080,refresh=59.94),dict(width=1280,height=720,refresh=60)],compositor='kwin')


class ProtocolTests(unittest.TestCase):
    def test_drained_failed_session_reports_failure_without_claiming_gpu_retirement(self):
        import uuid
        instance=uuid.uuid4()
        guest={'read_spec':lambda value: {'instance_id':str(value)}}
        with patch.object(p.runpy,'run_path',return_value={'stop_session':lambda value:{'drained':True}}), \
             patch.object(p,'session_unit_status',return_value={'state':'failed'}):
            result=p.session_stop(str(instance),guest)
        self.assertTrue(result['session_retired'])
        self.assertFalse(result['gpu_retired'])
        self.assertEqual(result['session_result'],'failed')
    def test_actual_json_stdin_stdout_roundtrip(self):
        code="import runpy;runpy.run_path(sys.argv[1])['serve']({})"
        result=subprocess.run([sys.executable,'-c','import sys;'+code,str(ROOT/'guest/protocol.py')],
            input=json.dumps(request()),text=True,capture_output=True,check=True)
        reply=json.loads(result.stdout)
        self.assertTrue(reply['ok']);self.assertEqual(reply['id'],'conformance-1')
        self.assertIn('session.stop',reply['result']['capabilities'])
        self.assertEqual(result.stderr,'')

    def test_new_optional_request_fields_do_not_break_old_guest(self):
        q=request();q['optional_extension']={'future':True}
        self.assertTrue(p.handle(q,{})['ok'])

    def test_invalid_major_minor_identity_and_operation_are_structured(self):
        for key,value in [('major',2),('major',True),('minor',1),('id','bad\nrequest'),('operation','shell.execute')]:
            q=request();q[key]=value
            with patch.object(p,'dispatch',wraps=p.dispatch) as call:
                result=p.handle(q,{})
                self.assertFalse(result['ok']);self.assertIn('code',result['error'])
                if key!='operation':call.assert_not_called()

    def test_stdout_contains_one_error_object_for_malformed_input(self):
        code="import sys,runpy;runpy.run_path(sys.argv[1])['serve']({})"
        for raw in ['{', 'x'*(p.LIMIT+1)]:
            r=subprocess.run([sys.executable,'-c',code,str(ROOT/'guest/protocol.py')],input=raw,text=True,capture_output=True,check=True)
            self.assertEqual(json.loads(r.stdout)['error']['code'],'invalid_request')

    def test_physical_modes_rational_scale_and_output_collection(self):
        value=p.display_snapshot(display());output=value['outputs'][0]
        telemetry = display()
        telemetry['monitor']['focused'] = True
        telemetry['monitor']['activeWorkspace'] = {'id': 9}
        self.assertEqual(value['generation'], p.display_snapshot(telemetry)['generation'])
        self.assertEqual(output['physical_size'],{'width':1920,'height':1080})
        self.assertEqual(output['scale'],{'numerator':5,'denominator':4})
        self.assertEqual(output['modes'][0]['refresh_millihz'],59940)
        other=display();other['monitor']['width']=1280
        self.assertNotEqual(value['generation'],p.display_snapshot(other)['generation'])

    def test_stale_generation_or_persistence_never_changes_display(self):
        with patch.object(p.runpy,'run_path') as load:
            adapter=load.return_value['execute'];adapter.return_value=display()
            result=p.handle(request('display.apply',{'instance':'test','expected_generation':'stale'}),{})
            self.assertEqual(result['error']['code'],'stale_generation');self.assertEqual(adapter.call_count,1)

    def test_apply_reuses_guest_adapter_and_acknowledges_actual_result(self):
        before=display();after=display();after['monitor'].update(width=1280,height=720,scale=1)
        snap=p.display_snapshot(before)
        params=dict(instance='test',expected_generation=snap['generation'],session_generation=snap['session_generation'],
                    output_id='output-a',mode_id='1',scale={'numerator':1,'denominator':1},persistence='backend-default')
        with patch.object(p.runpy,'run_path') as load:
            adapter=load.return_value['execute'];adapter.side_effect=[before,{},after]
            result=p.handle(request('display.apply',params),{})
            self.assertTrue(result['ok']);self.assertTrue(result['result']['applied'])
            self.assertEqual(result['result']['outputs'][0]['physical_size']['width'],1280)
            self.assertEqual(adapter.call_args_list[1].args[0]['fit']['mode']['width'],1280)

    def test_profile_mismatch_prevents_component_or_package_work(self):
        with patch.object(p,'profile',return_value=({},'actual')):
            result=p.handle(request('desktop.preflight',{'contract':{'guest_profile_sha256':'different'}}),{})
        self.assertEqual(result['error']['code'],'profile_mismatch')

    def test_adapter_failure_and_false_display_acknowledgement_are_errors(self):
        with patch.object(p.runpy, 'run_path') as load:
            load.return_value['execute'].side_effect = RuntimeError('Compositor disconnected')
            result = p.handle(request('display.query', {'instance':'test'}), {})
            self.assertEqual(result['error']['code'], 'guest_operation_failed')
        before = display(); snap = p.display_snapshot(before)
        params = dict(instance='test', expected_generation=snap['generation'],
                      session_generation=snap['session_generation'], output_id='output-a',
                      mode_id='1', scale={'numerator':1,'denominator':1}, persistence='backend-default')
        with patch.object(p.runpy, 'run_path') as load:
            load.return_value['execute'].side_effect = [before, {}, before]
            result = p.handle(request('display.apply', params), {})
            self.assertEqual(result['error']['code'], 'apply_not_confirmed')

    def test_session_retirement_does_not_claim_gpu_retirement(self):
        guest={'read_spec':lambda instance: {}}
        with patch.object(p.runpy,'run_path') as load, patch.object(p,'session_unit_status',return_value={'state':'stopped'}):
            result=p.handle(request('session.stop',{'instance':'11111111-1111-1111-1111-111111111111'}),guest)
        self.assertTrue(result['ok']);self.assertTrue(result['result']['session_retired'])
        self.assertFalse(result['result']['gpu_retired']);load.return_value['stop_session'].assert_called_once()

    def test_logout_may_remove_descriptor_before_status_confirmation(self):
        from unittest.mock import Mock
        reader=Mock(side_effect=[{}, FileNotFoundError('descriptor removed')])
        guest={'read_spec':reader}
        result=subprocess.CompletedProcess([],0,stdout='ActiveState=inactive\nSubState=dead\nResult=success\n')
        with patch.object(p.runpy,'run_path'), patch.object(p,'profile',return_value=({'implementation':'hyprland'},None)), patch.object(p.subprocess,'run',return_value=result):
            reply=p.handle(request('session.stop',{'instance':'11111111-1111-1111-1111-111111111111'}),guest)
        self.assertTrue(reply['ok'])
        self.assertTrue(reply['result']['session_retired'])
        self.assertFalse(reply['result']['gpu_retired'])
        self.assertEqual(reader.call_count,1)
        status=p.session_status('11111111-1111-1111-1111-111111111111',guest)
        self.assertEqual(status['state'],'unknown')
        self.assertFalse(status['gpu_retired'])


if __name__=='__main__':unittest.main()
