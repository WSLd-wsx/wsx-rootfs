"""Compiler-side collection creates only compact archives, with legacy readers intact."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import component_materials as materials
import compact_materials as compact
import shared_sources as shared
from license_fixture import seed
from license_inputs import paths as license_paths


def load(name):
    spec=importlib.util.spec_from_file_location(name,Path(__file__).resolve().parents[1]/'scripts'/name)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


class DirectCollection(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name);seed(self.root)
        boundary=self.root/'components/license-boundaries.json'
        policy=json.loads(boundary.read_text())
        policy['outputs'][0]['profiles']=['omarchy','cachyos-plasma']
        policy['outputs'][0]['installed_paths']=['usr/lib/wsx/runtime/*']
        boundary.write_text(json.dumps(policy))
        self.work=self.root/'work';(self.work/'source-archives').mkdir(parents=True)
        pins={}
        for name in shared.REFERENCE_ONLY|shared.RETAIN_ARCHIVE:
            archive=self.work/'source-archives'/(name+'.archive')
            with tarfile.open(archive,'w') as tar:
                shared.add_bytes(tar,name+'/LICENSE',b'Fixture retained upstream notice')
                shared.add_bytes(tar,name+'/source.c',b'Fixture original source')
            pins[name]=dict(sha256=materials.sha(archive),version='1',commit='abc',url='https://example.test/'+name)
        (self.root/'components/sources.json').write_text(json.dumps(dict(schema_version=1,**pins)))
        self.receipt=dict(origin='source-build',profile='omarchy',compiled=True,runtime_assembled=True,
            archives={c:dict(sha256=p['sha256']) for c,p in pins.items()},
            recipe_files={n:materials.sha(self.root/n) for n in license_paths(self.root)+['recipe.py','vendor/example.c']})
        for name in ('mesa/mesa-1/source.c','venus/mesa-1/source.c','hyprland/Hyprland-abc/source.c',
                     'kwin/prepared/source/consumer.cpp','mesa/build/generated.h'):
            p=self.work/'component-build'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'Build source fixture')
        for name in ('build-packages.txt','build-repositories.conf'):(self.work/name).write_text('fixture\n')
        for folder in ('mesa','venus','opaque-consumer'):
            p=self.work/'private'/folder;p.mkdir(parents=True);(p/'runtime').write_bytes(b'Binary fixture')
        self.receipt['runtime_files']={str(p.relative_to(self.work/'private')):materials.sha(p) for p in (self.work/'private').rglob('*') if p.is_file()}
        self.write_receipt()
        p=patch.object(compact,'ROOT',self.root);p.start();self.addCleanup(p.stop)

    def write_receipt(self):
        (self.work/'component-source.json').write_text(json.dumps(self.receipt))

    def test_direct_collection_has_no_monolithic_or_expanded_tree_copies(self):
        before=dict(self.receipt['runtime_files'])
        report=materials.prepare(self.work)
        self.assertEqual(report['schema_version'],2)
        self.assertFalse((self.work/'component-materials/sources.tar').exists())
        index=shared.verify_bundle(self.work/'component-materials/shared')
        names={r['path'] for f in index['files'] for r in f['entries']}
        self.assertNotIn('build-materials/mesa/mesa-1/source.c',names)
        self.assertNotIn('archives/hyprland.archive',names)
        self.assertIn('archives/mesa.archive',names)
        self.assertIn('build-materials/mesa/build/generated.h',names)
        self.assertIn('notices/upstream/hyprland/hyprland/LICENSE',names)
        self.assertEqual(materials.verify(self.work),report)
        self.assertEqual(before,{str(p.relative_to(self.work/'private')):materials.sha(p) for p in (self.work/'private').rglob('*') if p.is_file()})

    def test_kwin_delivery_retains_original_and_prepared_sources(self):
        self.receipt['profile']='cachyos-plasma';self.write_receipt()
        materials.prepare(self.work)
        index=shared.verify_bundle(self.work/'component-materials/shared')
        names={r['path'] for r in index['files'][2]['entries']}
        self.assertIn('archives/kwin.archive',names)
        self.assertIn('build-materials/kwin/prepared/source/consumer.cpp',names)

    def test_shared_export_is_copy_of_direct_output(self):
        materials.prepare(self.work)
        shared.make_bundle(self.work,self.root/'export')
        for name in (*shared.ARCHIVES,shared.INDEX):
            self.assertEqual(materials.sha(self.work/'component-materials/shared'/name),materials.sha(self.root/'export'/name))

    def test_changed_compact_archive_rejected(self):
        materials.prepare(self.work)
        (self.work/'component-materials/shared'/shared.ARCHIVES[1]).write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'changed'):materials.verify(self.work)

    def test_environment_restored_from_compact_materials(self):
        materials.prepare(self.work)
        load('reuse-components.py').restore_environment(self.work)
        self.assertEqual((self.work/'components/build-packages.txt').read_text(),'fixture\n')

    @unittest.skipUnless(shutil.which('zstd'),'zstd CLI required for real package round trip')
    def test_compact_private_package_roundtrip(self):
        materials.prepare(self.work)
        bundle=self.root/'bundle';load('package-source-components.py').package(self.work,bundle)
        self.assertFalse((bundle/'sources.tar').exists())
        manifest=json.loads((bundle/'manifest.json').read_text());self.assertEqual(manifest['schema_version'],2)
        admitted=self.root/'admitted';load('consume-source-components.py').consume(bundle,admitted,'omarchy',manifest['sha256'])
        self.assertEqual(materials.verify(admitted)['schema_version'],2)
        self.assertEqual(json.loads((admitted/'component-source.json').read_text()),self.receipt)
        self.assertFalse((admitted/'component-materials/sources.tar').exists())
        gate=load('private-artifact-gate.py')
        shutil.copytree(bundle,self.work/'packages');gate.verify_component(self.work)


class CollectionMigration(unittest.TestCase):
    def test_only_exact_collector_hash_pair_is_accepted(self):
        reuse=load('reuse-components.py')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'scripts').mkdir();(root/'components').mkdir()
            p=root/'scripts/component_materials.py';p.write_text('New collector fixture')
            (root/'components/source-delivery.json').write_text(json.dumps(dict(postbuild_collector_migration=dict(
                from_sha256=reuse.LEGACY_COLLECTOR_SHA256,to_sha256=materials.sha(p)))))
            self.assertTrue(reuse.collection_only_change(root,'scripts/component_materials.py',reuse.LEGACY_COLLECTOR_SHA256))
            self.assertFalse(reuse.collection_only_change(root,'scripts/build-components.py',reuse.LEGACY_COLLECTOR_SHA256))
            self.assertFalse(reuse.collection_only_change(root,'scripts/component_materials.py','0'*64))
            p.write_text('Unexpected collector change')
            self.assertFalse(reuse.collection_only_change(root,'scripts/component_materials.py',reuse.LEGACY_COLLECTOR_SHA256))
