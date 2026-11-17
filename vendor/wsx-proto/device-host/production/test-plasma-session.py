#!/usr/bin/env python3
"""Exercise instance isolation and configuration-before-start guardrails."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('plasma', Path(__file__).with_name('start-cachyos-plasma.py'))
plasma = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plasma)
ACCOUNT = SimpleNamespace(pw_name='wsx', pw_uid=1000, pw_gid=1000)


class SessionGuards(unittest.TestCase):
    def test_active_compositor_configuration_rejected(self):
        with patch.object(plasma, 'run'), patch.object(plasma.subprocess, 'run',
                return_value=SimpleNamespace(stdout='active\n')):
            with self.assertRaisesRegex(RuntimeError, 'existing compositor'):
                plasma.configure_plasma_service(ACCOUNT, {})

    def test_configuration_written_before_reload(self):
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root)
            def run(argv):
                if argv[-1] == 'daemon-reload':
                    content = (directory / 'wsx-opaque-candidate.conf').read_text()
                    self.assertIn('Environment="WSX_DESKTOP_INSTANCE=instance"', content)
                    self.assertIn('Environment="PATH=/private/%%stack"', content)
            with patch.object(plasma, 'Path', return_value=directory), \
                 patch.object(plasma.os, 'chown'), patch.object(plasma, 'run', side_effect=run), \
                 patch.object(plasma.subprocess, 'run', return_value=SimpleNamespace(stdout='inactive\n')):
                plasma.configure_plasma_service(ACCOUNT, {
                    'WSX_DESKTOP_INSTANCE': 'instance', 'PATH': '/private/%stack'})

    def test_logout_rejects_wrong_instance(self):
        with patch.object(plasma, 'run') as run, patch.object(plasma.subprocess, 'run',
                return_value=SimpleNamespace(stdout='WSX_DESKTOP_INSTANCE=other\n')):
            with self.assertRaisesRegex(RuntimeError, 'different desktop'):
                plasma.request_plasma_logout(ACCOUNT, 'instance')
            run.assert_not_called()

    def test_failed_service_is_not_retirement(self):
        with patch.object(plasma.subprocess, 'run',
                return_value=SimpleNamespace(returncode=0, stdout='failed\n')):
            with self.assertRaisesRegex(RuntimeError, 'failed during retirement'):
                plasma.wait_plasma_stopped(ACCOUNT)


if __name__ == '__main__':
    unittest.main()
