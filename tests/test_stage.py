"""Exercise generated desktop selection without starting a session or GPU."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class StageTests(unittest.TestCase):
    def test_linear_uses_pinned_compositor_without_opaque_admission(self):
        stage = module('stage_guest', ROOT/'scripts/stage-guest.py')
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            root = work/'root'; (root/'usr/bin').mkdir(parents=True)
            components = work/'components'
            for name in ('mesa', 'venus'):
                (components/name).mkdir(parents=True)
                (components/name/'manifest.json').write_text(json.dumps({'version':'fixture','files':{'fixture':'a'*64}}))
            consumer = components/'opaque-consumer'
            files = {}
            for name in ('bin/Hyprland', 'bin/hyprctl', 'lib/libaquamarine.so.14'):
                path = consumer/name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('fixture')
                files[name] = hashlib.sha256(b'fixture').hexdigest()
            (consumer/'manifest.json').write_text(json.dumps({'abi': 2, 'files': files}))
            with patch.object(sys,'argv',['stage',str(root),str(components)]), patch.object(stage.subprocess,'run'):
                stage.main()
            runtime = root/'usr/lib/wsx/runtime'
            profile = json.loads((root/'usr/lib/wsx/guest-profile.json').read_text())
            self.assertEqual(profile['implementation'], 'hyprland')
            self.assertEqual(set(profile['component_manifests']), {'mesa','venus','opaque-consumer'})
            for name, digest in profile['component_manifests'].items():
                self.assertEqual(digest, hashlib.sha256((runtime/name/'manifest.json').read_bytes()).hexdigest())
            generated = (runtime/'desktop.py').read_text()
            self.assertTrue(generated.startswith('# SPDX-License-Identifier: MIT\n'))
            self.assertIn('# Adapted by the WSX rootfs staging recipe from vendor/wsx-proto/device-host/production/start-guest.py.\n', generated)
            mesa = runtime/'mesa'
            names = ['lib/libgbm.so.1','lib/libEGL_mesa.so.0','lib/libGLX_mesa.so.0',
                     'lib/libgallium-26.1.8.so','share/glvnd/egl_vendor.d/50_mesa.json']
            hashes = {}
            for name in names:
                path = mesa/name; path.parent.mkdir(parents=True,exist_ok=True)
                path.write_bytes(b'fixture'); hashes[name]=hashlib.sha256(b'fixture').hexdigest()
            (mesa/'manifest.json').write_text(json.dumps({'version':'26.1.8','files':hashes}))
            venus=runtime/'venus'; files={}
            for name in ('libvulkan_virtio.so','virtio_icd.json'):
                (venus/name).write_bytes(b'fixture'); files[name]=hashlib.sha256(b'fixture').hexdigest()
            (venus/'manifest.json').write_text(json.dumps({'version':'26.2.4','zink_drm_identity':True,'files':files}))
            desktop=module('generated_desktop',runtime/'desktop.py')
            with patch.dict(os.environ,{'WSX_SHARING_PATH':'linear-v1'}):
                env=desktop.mesa_environment(runtime)
            self.assertEqual(env['WSX_COMPOSITOR_EXECUTABLE'],str(runtime/'opaque-consumer/bin/Hyprland'))
            self.assertNotIn('WSX_OPAQUE_COMPOSITOR',env)
            self.assertNotIn('WSX_ZINK_OPAQUE_SHARED',env)
            (runtime/'opaque-consumer/bin/Hyprland').write_text('corrupt')
            with patch.dict(os.environ,{'WSX_SHARING_PATH':'linear-v1'}):
                with self.assertRaisesRegex(RuntimeError,'hash mismatch'):
                    desktop.mesa_environment(runtime)
