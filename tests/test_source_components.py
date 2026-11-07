"""Source-route admission tests with fixtures; no network, compiler or GPU."""
import ast
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from license_fixture import seed

ROOT = Path(__file__).resolve().parents[1]


def module(filename):
    spec = importlib.util.spec_from_file_location(filename, ROOT/'scripts'/filename)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


assembler = module('assemble-source-components.py')
builder = module('build-components.py')


class SourceComponentsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.build = self.work/'component-build'
        self.build.mkdir()
        self.pins = json.loads((ROOT/'components/sources.json').read_text())

    def fixture(self):
        outputs = {}
        for name in assembler.COMPONENTS:
            prefix = self.build/name/'prefix'
            prefix.mkdir(parents=True)
            names = {'mesa':['lib/mesa.so'], 'venus':['libvulkan_virtio.so'],
                     'aquamarine':['lib/libaquamarine.so.14'], 'hyprland':['bin/Hyprland','bin/hyprctl']}[name]
            for relative in names:
                path = prefix/relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(name)
            report = dict(passed=True)
            if name in ('mesa','venus'):
                manifest = dict(version=self.pins[name]['version'], source_sha256=self.pins[name]['sha256'],
                    linear_shared_compat=True, opaque_gbm_export=True, opaque_consumer=True,
                    presentation_staging_policy=False, zink_drm_identity=True, opaque_wsi=True,
                    opaque_import=True, direct_wsi='linear-v1', files=assembler.files(prefix))
                (prefix/'manifest.json').write_text(json.dumps(manifest))
            else:
                report.update(revision=self.pins[name]['commit'], archive_sha256=self.pins[name]['sha256'])
            (self.build/name/'result.json').write_text(json.dumps(report))
            outputs[name] = {str(p.relative_to(prefix)):assembler.sha(p) for p in prefix.rglob('*') if p.is_file()}
        receipt = dict(origin='source-build', compiled=True,
            archives={n:dict(url=p['url'],sha256=p['sha256']) for n,p in self.pins.items() if n!='schema_version'},
            output_files=outputs, recipe_files={n:assembler.sha(ROOT/n) for n in (
                'components/sources.json','components/builder.json','scripts/build-components.py',
                'scripts/assemble-source-components.py')}, hardware_validation='not_run',
            license_review='pending', corresponding_source_complete=False)
        (self.build/'source-build.json').write_text(json.dumps(receipt))

    def test_assemble_keeps_validation_scopes_separate(self):
        self.fixture()
        assembler.assemble(self.build,self.work)
        receipt = json.loads((self.work/'component-source.json').read_text())
        self.assertTrue(receipt['runtime_assembled'])
        self.assertEqual(receipt['hardware_validation'],'not_run')
        self.assertFalse(receipt['corresponding_source_complete'])
        self.assertEqual(receipt['license_review'],'pending')
        self.assertNotIn('component_historical_evidence',receipt)
        runtime = self.work/'private/opaque-consumer'
        self.assertTrue((runtime/'bin/Hyprland').exists())
        self.assertTrue((runtime/'lib/libaquamarine.so.14').exists())
        self.assertEqual(json.loads((runtime/'manifest.json').read_text())['abi'],2)

    def test_cachyos_assembly_uses_only_paired_kwin(self):
        self.fixture()
        prefix=self.build/'kwin/prefix'
        for name in ('bin/kwin_wayland','lib/libkwin.so.6'):
            path=prefix/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('kwin fixture')
        (self.build/'kwin/result.json').write_text(json.dumps(dict(passed=True,
            version=self.pins['kwin']['version'],source_sha256=self.pins['kwin']['sha256'])))
        path=self.build/'source-build.json';receipt=json.loads(path.read_text())
        receipt['profile']='cachyos-plasma'
        receipt['output_files']['kwin']={str(p.relative_to(prefix)):assembler.sha(p) for p in prefix.rglob('*') if p.is_file()}
        path.write_text(json.dumps(receipt))
        assembler.assemble(self.build,self.work)
        self.assertEqual({p.name for p in (self.work/'private').iterdir()}, {'mesa','venus','kwin-opaque'})
        manifest=json.loads((self.work/'private/kwin-opaque/manifest.json').read_text())
        self.assertEqual(manifest['abi'],2)
        self.assertEqual(manifest['hardware_validation'],'not_run')

    def test_changed_output_rejected_before_assembly(self):
        self.fixture()
        (self.build/'hyprland/prefix/bin/Hyprland').write_text('tampered')
        with self.assertRaisesRegex(ValueError,'Compiled output changed'):
            assembler.assemble(self.build,self.work)
        self.assertFalse((self.work/'private').exists())

    def test_partial_build_is_not_admitted(self):
        self.fixture()
        (self.build/'hyprland/result.json').write_text('{"passed":false}')
        with self.assertRaisesRegex(ValueError,'Missing successful'):
            assembler.assemble(self.build,self.work)
        self.assertFalse((self.work/'component-source.json').exists())

    def test_escaping_link_rejected(self):
        self.fixture()
        (self.build/'mesa/prefix/escape').symlink_to(self.work/'component-build/source-build.json')
        with self.assertRaisesRegex(ValueError,'escapes'):
            assembler.assemble(self.build,self.work)

    def test_merge_conflict_is_not_overwritten(self):
        one=self.work/'one';two=self.work/'two'
        one.mkdir();two.mkdir()
        (one/'same').write_text('one');(two/'same').write_text('two')
        target=self.work/'merged'
        assembler.merge_prefix(one,target)
        with self.assertRaisesRegex(ValueError,'Conflicting'):
            assembler.merge_prefix(two,target)
        self.assertEqual((target/'same').read_text(),'one')

    def test_bad_source_archive_fails_before_compiler(self):
        archives=self.work/'archives';archives.mkdir()
        (archives/'mesa.archive').write_bytes(b'wrong source')
        with patch.object(sys,'argv',['build','--archives',str(archives),'--output',str(self.work/'out')]), patch.object(builder,'build') as compile:
            with self.assertRaisesRegex(ValueError,'Source archive hash mismatch'):
                builder.main()
            compile.assert_not_called()
        self.assertFalse((self.work/'out').exists())

    def test_compiler_failure_retains_incomplete_receipt(self):
        repository=self.work/'repository';(repository/'components').mkdir(parents=True)
        archives=self.work/'archives';archives.mkdir()
        (archives/'fixture.archive').write_bytes(b'source')
        (repository/'components/sources.json').write_text(json.dumps(dict(schema_version=1,
            fixture=dict(url='https://example.invalid/source',sha256=assembler.sha(archives/'fixture.archive')))))
        seed(repository)
        out=self.work/'failed-build'
        with patch.object(builder,'ROOT',repository), patch.object(builder,'build',side_effect=RuntimeError('compiler fixture failure')), patch.object(sys,'argv',['build','--archives',str(archives),'--output',str(out)]):
            with self.assertRaisesRegex(RuntimeError,'compiler fixture failure'):
                builder.main()
        receipt=json.loads((out/'source-build.json').read_text())
        self.assertFalse(receipt['compiled'])
        self.assertFalse(receipt['runtime_assembled'])
        self.assertEqual(receipt['error'],'compiler fixture failure')
        self.assertEqual(receipt['hardware_validation'],'not_run')

    def test_disposable_builders_have_portable_inputs_and_preserve_safety_flags(self):
        archives=self.work/'archives';archives.mkdir()
        with tarfile.open(archives/'glaze.archive','w') as archive:
            info=tarfile.TarInfo('glaze/source');info.size=1
            archive.addfile(info,io.BytesIO(b'x'))
        commands=[]
        def run(*args):
            command=list(map(str,args));commands.append(command)
            text=Path(command[1]).read_text();ast.parse(text)
            if command[1].endswith('/guest-compat/build.py'):
                self.assertNotIn("pin = json.loads((ROOT / 'prototypes/",text)
                self.assertNotIn("archive = ROOT / 'artifacts/",text)
                self.assertIn('--opaque-consumer',command)
                self.assertNotIn('--presentation-staging',command)
                self.assertNotIn('--gbm-shared-contract',command)
            if command[1].endswith('build-compositor.py'):
                self.assertIn('-DCMAKE_SKIP_RPATH=ON',text)
        with patch.object(builder,'run',run):
            builder.build(SimpleNamespace(archives=archives,output=self.build))
        self.assertEqual(len(commands),4)
        self.assertIn('--opaque-wsi',commands[1])

    def test_cachyos_recipe_requires_pinned_source(self):
        support = module('source_support.py')
        support.require_source_recipe('wsx-cachyos-plasma')
        with patch.object(support, 'ROOT', self.work):
            (self.work/'components').mkdir()
            (self.work/'components/sources.json').write_text('{}')
            with self.assertRaisesRegex(ValueError, 'Missing pinned KWin'):
                support.require_source_recipe('wsx-cachyos-plasma')

    def test_cachyos_bootstrap_guard_runs_under_errexit(self):
        text=(ROOT/'distros/cachyos-plasma/bootstrap-rootfs.sh').read_text()
        self.assertLess(text.index('set -euo pipefail'),text.index('scripts/source-support.py'))
        self.assertLess(text.index('pacman -Syu --noconfirm --needed archlinux-keyring arch-install-scripts python'),text.index('scripts/source-support.py'))
        self.assertLess(text.index('scripts/source-support.py'),text.index('pacstrap -c'))

    def test_active_routes_do_not_fetch_retired_package(self):
        for directory in ('.github/workflows','scripts','distros/omarchy','components'):
            for path in (ROOT/directory).rglob('*'):
                if path.is_file() and path.suffix in ('.py','.yml','.sh','.json'):
                    text=path.read_text()
                    self.assertNotIn('ghcr.io/wsld-wsx/wsx-rootfs/verified-components',text,str(path))
                    self.assertNotIn('components/package.json',text,str(path))
                    self.assertNotIn('component-desktop-evidence.json',text,str(path))
