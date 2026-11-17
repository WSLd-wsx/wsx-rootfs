# SPDX-License-Identifier: MIT
"""Verify D-Bus activation in a disposable bus, without touching a user bus."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


class IsolatedBusTests(unittest.TestCase):
    @unittest.skipUnless(all(shutil.which(x) for x in ('dbus-run-session', 'dbus-update-activation-environment')),
                         'D-Bus test tools unavailable')
    def test_activated_application_receives_venus_setting(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            services = root / 'share/dbus-1/services'
            services.mkdir(parents=True)
            output = root / 'activation-env.txt'
            application = root / 'activated.py'
            application.write_text("#!/usr/bin/python3\nimport os\nfrom pathlib import Path\nPath(os.environ['WSX_TEST_OUTPUT']).write_text(os.environ.get('VN_PERF', '<missing>'))\n")
            application.chmod(0o755)
            (services / 'org.wsx.EnvironmentProbe.service').write_text(
                '[D-BUS Service]\nName=org.wsx.EnvironmentProbe\nExec=' + str(application) + '\n')
            env = dict(os.environ, XDG_DATA_DIRS=str(root / 'share'),
                       VN_PERF='no_async_mem_alloc', WSX_TEST_OUTPUT=str(output))
            # The service writes its environment and exits without taking its bus name;
            # the expected activation error is irrelevant to the environment check.
            script = ('dbus-update-activation-environment VN_PERF WSX_TEST_OUTPUT; '
                      'dbus-send --session --print-reply --reply-timeout=3000 '
                      '--dest=org.freedesktop.DBus /org/freedesktop/DBus '
                      'org.freedesktop.DBus.StartServiceByName '
                      'string:org.wsx.EnvironmentProbe uint32:0 >/dev/null 2>&1 || :')
            subprocess.run(['dbus-run-session', '--', 'sh', '-c', script], env=env,
                           check=True, timeout=10, capture_output=True, text=True)
            self.assertEqual(output.read_text(), 'no_async_mem_alloc')
            output.unlink()
            fresh_env = dict(env)
            fresh_env.pop('VN_PERF')
            fresh_script = script.replace('VN_PERF WSX_TEST_OUTPUT', 'WSX_TEST_OUTPUT', 1)
            subprocess.run(['dbus-run-session', '--', 'sh', '-c', fresh_script],
                           env=fresh_env, check=True, timeout=10,
                           capture_output=True, text=True)
            self.assertEqual(output.read_text(), '<missing>')


    @unittest.skipUnless(all(shutil.which(x) for x in ('dbus-run-session', 'dbus-update-activation-environment')),
                         'D-Bus test tools unavailable')
    def test_activation_environment_changes_on_same_bus(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            services = root / 'share/dbus-1/services'
            services.mkdir(parents=True)
            output = root / 'values.txt'
            app = root / 'application.py'
            app.write_text("#!/usr/bin/python3\nimport os\nwith open(os.environ['WSX_TEST_OUTPUT'], 'a') as f: f.write(os.environ.get('VN_PERF', '<missing>') + '\\n')\n")
            app.chmod(0o755)
            for name in ('Staging', 'Opaque'):
                bus_name = 'org.wsx.' + name
                (services / (bus_name + '.service')).write_text(
                    '[D-BUS Service]\nName=' + bus_name + '\nExec=' + str(app) + '\n')
            env = dict(os.environ, XDG_DATA_DIRS=str(root / 'share'), WSX_TEST_OUTPUT=str(output))
            activate = ('dbus-send --session --print-reply --reply-timeout=3000 '
                        '--dest=org.freedesktop.DBus /org/freedesktop/DBus '
                        'org.freedesktop.DBus.StartServiceByName ')
            script = ('dbus-update-activation-environment WSX_TEST_OUTPUT VN_PERF=no_async_mem_alloc; '
                      + activate + 'string:org.wsx.Staging uint32:0 >/dev/null 2>&1 || :; '
                      'dbus-update-activation-environment VN_PERF=; '
                      + activate + 'string:org.wsx.Opaque uint32:0 >/dev/null 2>&1 || :')
            subprocess.run(['dbus-run-session', '--', 'sh', '-c', script], env=env,
                           check=True, timeout=10, capture_output=True, text=True)
            self.assertEqual(output.read_text().splitlines(), ['no_async_mem_alloc', ''])


if __name__ == '__main__':
    unittest.main()
