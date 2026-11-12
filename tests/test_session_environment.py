# SPDX-License-Identifier: MIT
"""Check the desktop launcher passes the selected Venus session setting."""
import json
import importlib.util
from unittest.mock import patch
import os
from pathlib import Path
import subprocess
import runpy
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class LauncherEnvironmentTests(unittest.TestCase):
    def test_uwsm_launcher_preserves_only_explicit_session_value(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            session = tmp / 'session'
            shutil.copytree(ROOT / 'vendor/wsx-proto/session', session)
            runpy.run_path(str(ROOT / 'scripts/session_venus_policy.py'))['configure'](session)
            source = (session / 'wsx-launch-app').read_text()
            mock = tmp / 'uwsm-app'
            mock.write_text('#!/bin/bash\nshift 3\nexec "$@"\n')
            mock.chmod(0o755)
            launcher = tmp / 'launcher'
            launcher.write_text(source.replace('/usr/bin/uwsm-app', str(mock)))
            launcher.chmod(0o755)
            command = ['/usr/bin/python3', '-c',
                       'import json,os; print(json.dumps(os.environ.get("VN_PERF")))']
            env = dict(os.environ, XDG_RUNTIME_DIR='/tmp/wsx-test', VN_PERF='no_async_mem_alloc')
            result = subprocess.run([str(launcher), *command], env=env,
                                    text=True, capture_output=True, check=True)
            self.assertEqual(json.loads(result.stdout), 'no_async_mem_alloc')
            env.pop('VN_PERF')
            result = subprocess.run([str(launcher), *command], env=env,
                                    text=True, capture_output=True, check=True)
            self.assertIsNone(json.loads(result.stdout))


    def _temporary_session_cleanup(self):
        self._temporary_session.cleanup()

    def test_session_entry_publishes_policy_before_compositor(self):
        self.addCleanup(self._temporary_session_cleanup)
        self._temporary_session = tempfile.TemporaryDirectory()
        session = Path(self._temporary_session.name) / 'session'
        shutil.copytree(ROOT / 'vendor/wsx-proto/session', session)
        runpy.run_path(str(ROOT / 'scripts/session_venus_policy.py'))['configure'](session)
        path = session / 'enter.py'
        spec = importlib.util.spec_from_file_location('session_entry', path)
        entry = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(entry)
        for value in ('no_async_mem_alloc', ''):
            env = {'XDG_SESSION_ID': 'test', 'VN_PERF': value}
            with patch.dict(entry.os.environ, env, clear=True), \
                 patch.object(entry.os, 'getuid', return_value=1000), \
                 patch.object(entry.Path, 'stat') as stat, \
                 patch.object(entry.Path, 'is_symlink', return_value=False), \
                 patch.object(entry.subprocess, 'run') as run, \
                 patch.object(entry.os, 'execvpe') as execute, \
                 patch.object(entry.sys, 'argv', ['enter.py', '/bin/compositor']):
                stat.return_value.st_uid = 1000
                entry.main()
                run.assert_called_once_with(
                    ['/usr/bin/dbus-update-activation-environment', '--systemd', 'VN_PERF'],
                    check=True, timeout=10)
                self.assertEqual(execute.call_args.args[2]['VN_PERF'], value)


if __name__ == '__main__':
    unittest.main()
