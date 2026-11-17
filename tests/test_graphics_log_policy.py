"""Graphics traces are opt-in and cannot change the patched error paths."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import graphics_log_policy as policy
import graphics_debug


class GraphicsLogPolicy(unittest.TestCase):
    def test_desktop_diagnostics_are_opt_in_for_both_profiles(self):
        from unittest.mock import patch
        for script in ('start-guest.py', 'start-cachyos-plasma.py'):
            original = (ROOT / 'vendor/wsx-proto/device-host/production' / script).read_text()
            adapted = graphics_debug.configure(original)
            self.assertEqual(adapted.count("VN_DEBUG='init,result'"), 1)
            self.assertIn("trace_config = Path('/etc/wsx/graphics-trace')", adapted)
        statement = '\n'.join(line[4:] if line.startswith('    ') else line for line in graphics_debug.OPT_IN.splitlines())
        for value in (None, '0', '1'):
            namespace = {'env': {}, 'private_mesa': {}, 'Path': Path}
            with patch.object(Path, 'is_file', return_value=value is not None), \
                 patch.object(Path, 'read_text', return_value=value or ''):
                exec(statement, namespace)
            self.assertEqual(namespace['env'].get('WSX_GRAPHICS_TRACE'), '1' if value == '1' else None)
            self.assertEqual('VN_DEBUG' in namespace['env'], value == '1')

    def test_all_known_sites_match_vendored_patch_content(self):
        fragments = {}
        for patch in (ROOT / 'vendor/wsx-proto/guest-compat').glob('*.patch'):
            relative = None
            for line in patch.read_text().splitlines(keepends=True):
                if line.startswith('+++ b/'):
                    relative = line[6:].strip()
                elif relative and line.startswith('+') and not line.startswith('+++'):
                    fragments.setdefault(relative, []).append(line[1:])
        with tempfile.TemporaryDirectory() as temporary:
            for profile, paths in policy.TARGETS.items():
                tree = Path(temporary) / profile
                for relative in paths:
                    target = tree / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(''.join(fragments[relative]))
                policy.apply(tree, profile)

    def test_known_patch_sites_are_gated_and_errors_remain(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for profile, paths in policy.TARGETS.items():
                tree = root / profile
                for relative, markers in paths.items():
                    target = tree / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    calls = ['mesa_logi("WSX_' + marker + ' details");' for marker in markers]
                    target.write_text('\n'.join(calls) + '\nmesa_loge("failure");\n')
                self.assertEqual(set(policy.apply(tree, profile)), set(paths))
                for relative, markers in paths.items():
                    text = (tree / relative).read_text()
                    self.assertEqual(text.count('WSX_TRACE_LOG(mesa_logi,'), len(markers))
                    self.assertIn('mesa_loge("failure");', text)
                with self.assertRaisesRegex(ValueError, 'already applied'):
                    policy.apply(tree, profile)

    @unittest.skipUnless(shutil.which('cc'), 'C compiler unavailable')
    def test_switch_is_disabled_by_default_and_enabled_only_by_one(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / 'test.c'
            executable = Path(temporary) / 'test'
            source.write_text(policy.PREFIX + '#include <stdio.h>\n'
                              'int main(void) { WSX_TRACE_LOG(puts, "trace"); return 0; }\n')
            subprocess.run(['cc', '-Wall', '-Werror', str(source), '-o', str(executable)], check=True)
            for value, expected in [(None, ''), ('0', ''), ('1', 'trace\n')]:
                import os
                env = dict(os.environ)
                env.pop(policy.TRACE, None)
                if value is not None:
                    env[policy.TRACE] = value
                self.assertEqual(subprocess.check_output([str(executable)], env=env, text=True), expected)

    def test_missing_site_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for relative in policy.TARGETS['mesa']:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('int unchanged;\n')
            with self.assertRaisesRegex(ValueError, 'Unexpected graphics trace site'):
                policy.apply(root, 'mesa')


if __name__ == '__main__':
    unittest.main()
