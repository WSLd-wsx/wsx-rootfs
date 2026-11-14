"""Pinned component reuse must never silently compile or select a different build."""
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile
from unittest.mock import patch
from license_fixture import seed

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
spec=importlib.util.spec_from_file_location('reuse_components',ROOT/'scripts/reuse-components.py')
reuse=importlib.util.module_from_spec(spec);spec.loader.exec_module(reuse)


class ReuseTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.root=Path(temp.name)
        self.pin=dict(run_id=10,artifact_id=20,source_commit='a'*40,manifest_sha256='b'*64)
        self.run=dict(conclusion='success',status='completed',event='workflow_dispatch',
                      path='.github/workflows/components.yml',head_sha='a'*40,
                      repository=dict(full_name='owner/repo'),head_repository=dict(full_name='owner/repo'))
        self.artifact=dict(id=20,expired=False,name='omarchy-source-components-'+'a'*40,
                           workflow_run=dict(id=10,head_sha='a'*40))

    def test_origin_accepts_only_successful_matching_component_run(self):
        reuse.validate_origin(self.pin,'omarchy','owner/repo',self.run,self.artifact)
        for key,value in [('conclusion','failure'),('event','pull_request'),('head_sha','c'*40),
                          ('path','.github/workflows/other.yml')]:
            with self.subTest(key=key),self.assertRaises(ValueError):
                reuse.validate_origin(self.pin,'omarchy','owner/repo',dict(self.run,**{key:value}),self.artifact)
        for change in [dict(expired=True),dict(id=21),dict(workflow_run=dict(id=11,head_sha='a'*40))]:
            with self.assertRaises(ValueError):
                reuse.validate_origin(self.pin,'omarchy','owner/repo',self.run,dict(self.artifact,**change))

    def test_operations_origin_binds_workflow_and_source_separately(self):
        pin = dict(transport='ghcr', run_id=10, source_commit='a'*40,
                   workflow_commit='b'*40, run_repository='WSLd-wsx/wsx-rootfs-ops',
                   image=reuse.registry.OPS_IMAGE+'@sha256:'+'c'*64)
        run = dict(status='completed', conclusion='success', event='workflow_dispatch',
                   path='.github/workflows/components.yml', head_sha='b'*40, head_branch='main',
                   repository=dict(full_name=pin['run_repository']),
                   head_repository=dict(full_name=pin['run_repository']))
        reuse.validate_origin(pin, 'omarchy', 'WSLd-wsx/wsx-rootfs', run, {})
        renamed = dict(full_name='WSLd-wsx/wsx-devops', id=1449208538)
        reuse.validate_origin(pin, 'omarchy', 'WSLd-wsx/wsx-rootfs',
                              dict(run, repository=renamed, head_repository=renamed), {})
        with self.assertRaisesRegex(ValueError, 'origin mismatch'):
            reuse.validate_origin(pin, 'omarchy', 'WSLd-wsx/wsx-rootfs',
                                  dict(run, repository=dict(renamed, id=1), head_repository=renamed), {})
        for changed in (dict(pin, workflow_commit='d'*40),
                        dict(pin, run_repository='other/repo'),
                        dict(pin, image=reuse.registry.IMAGE+'@sha256:'+'c'*64)):
            with self.assertRaises(ValueError):
                reuse.validate_origin(changed, 'omarchy', 'WSLd-wsx/wsx-rootfs', run, {})
        with self.assertRaisesRegex(ValueError, 'main branch'):
            reuse.validate_origin(pin, 'omarchy', 'WSLd-wsx/wsx-rootfs', dict(run, head_branch='unreviewed'), {})

    def test_registry_reuse_binds_published_receipt_without_live_run_dependency(self):
        import shared_sources
        (self.root/'components').mkdir()
        pin=dict(transport='ghcr',run_id=10,source_commit='a'*40,
                 image=reuse.registry.IMAGE+'@sha256:'+'b'*64)
        (self.root/'components/source-delivery.json').write_text(json.dumps(dict(component_origins={'omarchy':pin})))
        with patch.object(shared_sources,'pin_for',return_value={}), patch.object(shared_sources,'download_index',return_value=b'{"verified":"index"}'):
            self.assertEqual(reuse.published_registry_origin(self.root,pin,'omarchy'),{'verified':'index'})
            migrated=dict(pin,image=reuse.registry.OPS_IMAGE+'@sha256:'+'b'*64)
            self.assertEqual(reuse.published_registry_origin(self.root,migrated,'omarchy'),{'verified':'index'})
            with self.assertRaisesRegex(ValueError,'source origin'):
                reuse.published_registry_origin(self.root,dict(migrated,image=reuse.registry.OPS_IMAGE+'@sha256:'+'c'*64),'omarchy')
            with self.assertRaisesRegex(ValueError,'source origin'):
                reuse.published_registry_origin(self.root,dict(pin,run_id=11),'omarchy')
        work=self.root/'work';work.mkdir()
        receipt=dict(compiled=True,profile='omarchy');(work/'component-source.json').write_text(json.dumps(receipt))
        index=dict(component_receipt=receipt,source_receipt_sha256=reuse.sha(work/'component-source.json'))
        reuse.verify_published_receipt(index,work)
        (work/'component-source.json').write_text(json.dumps(dict(receipt,compiled=False)))
        with self.assertRaisesRegex(ValueError,'published source receipt'):
            reuse.verify_published_receipt(index,work)

    def test_missing_pin_fails_before_network(self):
        (self.root/'components').mkdir()
        (self.root/'components/reuse.json').write_text(json.dumps(dict(schema_version=1,profiles={'omarchy':None})))
        with patch.object(reuse.subprocess,'check_output') as call:
            with self.assertRaisesRegex(ValueError,'No pinned'):
                reuse.acquire(self.root,self.root/'out','omarchy','owner/repo')
            call.assert_not_called()

    def test_zip_rejects_escape_duplicates_and_links(self):
        for name,mode in [('../escape',0),('folder/file',0),('link',0o120777<<16)]:
            data=io.BytesIO()
            with zipfile.ZipFile(data,'w') as archive:
                info=zipfile.ZipInfo(name);info.external_attr=mode;archive.writestr(info,'fixture')
            data.seek(0)
            with self.assertRaisesRegex(ValueError,'Unsafe'):
                reuse.unpack(data,self.root)

    def test_rootfs_workflows_never_compile_components(self):
        for name in ('build-rootfs.yml','cachyos-plasma.yml'):
            text=(ROOT/'components/workflow-history/20261107'/name).read_text()
            self.assertNotIn('build-components.sh',text)
            self.assertNotIn('package-source-components.py',text)
            self.assertIn('reuse-components.py --profile',text)
            self.assertIn('actions: read',text)
        self.assertIn('build-components.sh',(ROOT/'components/workflow-history/20261107/components.yml').read_text())

    def test_compatibility_allows_image_recipe_changes_but_rejects_component_changes(self):
        seed(self.root)
        (self.root/'components/sources.json').write_text('{}')
        (self.root/'components/builder.json').write_text('{}')
        (self.root/'compile.py').write_text('# component compiler\n')
        (self.root/'image.py').write_text('# rootfs-only recipe\n')
        import product_licenses as product
        boundary=self.root/'components/license-boundaries.json'
        data=json.loads(boundary.read_text());data['roots']={'paired-component-build':['compile.py']}
        data['outputs'][0]['installed_paths']=['usr/lib/wsx/runtime/fixture']
        boundary.write_text(json.dumps(data))
        names=reuse.license_paths(self.root)+['components/sources.json','components/builder.json',
                                            'compile.py','image.py','vendor/example.c']
        work=self.root/'work';notices=work/'component-materials/notices';notices.mkdir(parents=True)
        receipt=dict(profile='omarchy',runtime_files={'fixture':'a'*64},
                     recipe_files={n:reuse.sha(self.root/n) for n in names})
        (work/'component-source.json').write_text(json.dumps(receipt))
        product.write_component_map(self.root,receipt,notices)
        reuse.check_compatibility(self.root,work)
        (self.root/'image.py').write_text('# updated image recipe\n')
        reuse.check_compatibility(self.root,work)
        # New image outputs and their scoped metadata do not rebuild old binaries.
        data['outputs'].append(dict(id='image-only',profiles=['omarchy'],installed_paths=['usr/bin/image'],
                                    source_paths=['image.py'],kind='script',license_treatment='Fixture'))
        boundary.write_text(json.dumps(data))
        with (self.root/'LICENSE-MAP.md').open('a') as stream:stream.write('Additional image notice\n')
        reuse.check_compatibility(self.root,work)
        # Changing the rights on an existing compiled source still rejects.
        policy=self.root/'docs/licensing/modules.json';saved=policy.read_text();changed=json.loads(saved)
        changed['path_overrides']['vendor/example.c']='wsx-independent';policy.write_text(json.dumps(changed))
        with self.assertRaisesRegex(ValueError,'license classification'):
            reuse.check_compatibility(self.root,work)
        policy.write_text(saved)

        (self.root/'compile.py').write_text('# changed component compiler\n')
        with self.assertRaisesRegex(ValueError,'boundary differs.*compile.py'):
            reuse.check_compatibility(self.root,work)
