"""Shared sources retain required inputs and fail closed on unavailable references."""
import copy
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from urllib.error import HTTPError
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import shared_sources as shared
import source_delivery as delivery
from component_materials import sha
from payload_contract import asset_names, SHARED_SOURCE_ASSETS
from test_contract import manifest


class SharedSources(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name);self.repo=self.root/'repo';(self.repo/'components').mkdir(parents=True)
        self.work=self.root/'work';self.material=self.work/'component-materials'
        (self.material/'notices').mkdir(parents=True)
        (self.material/'notices/LICENSE').write_text('Retained original notice')
        self.pins={c:dict(version='1',commit='abc',url='https://example.test/'+c,
                         sha256=hashlib.sha256(c.encode()).hexdigest()) for c in shared.REFERENCE_ONLY|shared.RETAIN_ARCHIVE}
        (self.repo/'components/sources.json').write_text(json.dumps(dict(schema_version=1,**self.pins)))
        self.patch=patch.object(shared,'ROOT',self.repo);self.patch.start();self.addCleanup(self.patch.stop)
        self.fixture('omarchy')

    def fixture(self,profile):
        self.receipt=dict(profile=profile,origin='source-build',compiled=True,runtime_assembled=True,
                          archives={c:dict(sha256=p['sha256']) for c,p in self.pins.items()})
        (self.work/'component-source.json').write_text(json.dumps(self.receipt))
        files={f'archives/{c}.archive':c.encode() for c in self.pins}
        files.update({'recipe/vendor/adapter.patch':b'Original patch',
            'build-materials/mesa/mesa-1/source.c':b'Expanded upstream',
            'build-materials/mesa/build/generated.h':b'Generated source',
            'build-materials/kwin/prepared/source/consumer.cpp':b'Patched GPL source',
            'build-materials/hyprland/Hyprland-abc/main.cpp':b'Expanded permissive source',
            'build-materials/builders/build.py':b'Original adapted builder'})
        records=[]
        with tarfile.open(self.material/'sources.tar','w') as tar:
            for name,data in sorted(files.items()):
                row=shared.add_bytes(tar,name,data);records.append({k:row[k] for k in ('path','sha256','size')})
        report=dict(schema_version=1,collection_complete=True,source_entries=records,
            source_receipt_sha256=sha(self.work/'component-source.json'),
            sources=dict(path='sources.tar',sha256=sha(self.material/'sources.tar'),size=(self.material/'sources.tar').stat().st_size),
            notice_files={'LICENSE':sha(self.material/'notices/LICENSE')})
        (self.material/'materials.json').write_text(json.dumps(report))

    def test_permissive_omissions_and_original_package_unchanged(self):
        before=sha(self.material/'sources.tar')
        index=shared.make_bundle(self.work,self.root/'bundle')
        retained={x['path'] for x in index['files'][2]['entries']}
        changes={x['path'] for x in index['files'][1]['entries']}
        self.assertEqual(retained,{'archives/mesa.archive','archives/venus.archive'})
        self.assertIn('recipe/vendor/adapter.patch',changes)
        self.assertIn('build-materials/mesa/build/generated.h',changes)
        self.assertNotIn('build-materials/mesa/mesa-1/source.c',changes)
        self.assertEqual(sha(self.material/'sources.tar'),before)
        self.assertEqual(index['upstream']['hyprland']['delivery'],'fixed-source-reference')

    def test_kwin_original_and_patched_sources_retained(self):
        self.fixture('cachyos-plasma')
        index=shared.make_bundle(self.work,self.root/'bundle')
        retained={x['path'] for x in index['files'][2]['entries']}
        self.assertIn('archives/kwin.archive',retained)
        self.assertIn('build-materials/kwin/prepared/source/consumer.cpp',retained)

    def test_same_component_sources_are_deterministic(self):
        first=shared.make_bundle(self.work,self.root/'one')
        second=shared.make_bundle(self.work,self.root/'two')
        self.assertEqual(first,second)
        self.assertEqual(sha(self.root/'one'/shared.INDEX),sha(self.root/'two'/shared.INDEX))

    def test_changed_policy_pin_blocks_projection(self):
        self.pins['mesa']['sha256']='0'*64
        (self.repo/'components/sources.json').write_text(json.dumps(dict(schema_version=1,**self.pins)))
        with self.assertRaisesRegex(ValueError,'upstream inputs changed'):
            shared.make_bundle(self.work,self.root/'bundle')

    def test_corrupt_source_member_blocks_even_if_outer_hash_updated(self):
        report=json.loads((self.material/'materials.json').read_text())
        report['source_entries'][0]['sha256']='0'*64
        (self.material/'materials.json').write_text(json.dumps(report))
        with self.assertRaisesRegex(ValueError,'source member differs'):
            shared.make_bundle(self.work,self.root/'bundle')

    def test_mutated_shared_archive_rejected(self):
        shared.make_bundle(self.work,self.root/'bundle')
        (self.root/'bundle'/shared.ARCHIVES[2]).write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'archive changed'):
            shared.verify_bundle(self.root/'bundle')

    def prepared(self):
        bundle=self.root/'bundle';index=shared.make_bundle(self.work,bundle)
        pin=dict(tag=index['tag'],manifest_sha256=sha(bundle/shared.INDEX))
        return bundle,index,pin

    def release(self,index,pin,draft=False):
        records=list(index['files'])+[dict(name=shared.INDEX,sha256=pin['manifest_sha256'],size=1)]
        return dict(tag_name=index['tag'],draft=draft,assets=[dict(name=f['name'],state='uploaded',size=f['size'],
            digest='sha256:'+f['sha256'],browser_download_url=f'https://github.com/{shared.REPOSITORY}/releases/download/{pin["tag"]}/{f["name"]}') for f in records])

    def test_private_or_draft_reference_rejected(self):
        _,index,pin=self.prepared()
        for private,draft in [(True,False),(False,True)]:
            with patch.object(shared,'public_json',side_effect=[dict(full_name=shared.REPOSITORY,private=private),self.release(index,pin,draft)]):
                with self.assertRaisesRegex(ValueError,'publicly accessible'):
                    shared.verify_public(pin,index)

    def test_private_reference_requires_private_repository_and_exact_assets(self):
        _, index, pin = self.prepared()
        private = dict(full_name=shared.REPOSITORY, private=True)
        release = self.release(index, pin)
        with patch.object(shared, 'private_json', side_effect=[private, release]):
            shared.verify_private(pin, index)
        with patch.object(shared, 'private_json', side_effect=[dict(private, private=False), release]):
            with self.assertRaisesRegex(ValueError, 'private release'):
                shared.verify_private(pin, index)
        release['assets'][0]['digest'] = 'sha256:' + '0' * 64
        with patch.object(shared, 'private_json', side_effect=[private, release]):
            with self.assertRaisesRegex(ValueError, 'asset missing or changed'):
                shared.verify_private(pin, index)

    def test_private_index_download_checks_digest_and_origin(self):
        bundle, index, pin = self.prepared()
        release = self.release(index, pin)
        for asset in release['assets']:
            asset['id'] = 1
        private = dict(full_name=shared.REPOSITORY, private=True)
        with patch.dict('os.environ', {'WSX_PRIVATE_SOURCE': '1', 'GH_TOKEN': 'test'}), \
             patch.object(shared, 'private_json', side_effect=[private, release, private, release]), \
             patch.object(shared.subprocess, 'check_output', return_value=(bundle / shared.INDEX).read_bytes()):
            self.assertEqual(json.loads(shared.download_index(pin, 'omarchy')), index)
        with patch.dict('os.environ', {'WSX_PRIVATE_SOURCE': '1', 'GH_TOKEN': 'test'}), \
             patch.object(shared, 'private_json', side_effect=[private, release]), \
             patch.object(shared.subprocess, 'check_output', return_value=b'changed'):
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                shared.download_index(pin, 'omarchy')

    def test_public_reference_requires_exact_remote_asset_hashes(self):
        _,index,pin=self.prepared();release=self.release(index,pin)
        metadata=dict(full_name=shared.REPOSITORY,private=False)
        with patch.object(shared,'public_json',side_effect=[metadata,release]):shared.verify_public(pin,index)
        release['assets'][0]['digest']='sha256:'+'0'*64
        with patch.object(shared,'public_json',side_effect=[metadata,release]):
            with self.assertRaisesRegex(ValueError,'missing or changed'):shared.verify_public(pin,index)

    def test_public_download_falls_back_only_to_verified_anonymous_asset(self):
        bundle, index, pin = self.prepared()
        content = (bundle/shared.INDEX).read_bytes()
        release = self.release(index, pin)
        index_asset = next(a for a in release['assets'] if a['name'] == shared.INDEX)
        index_asset.update(id=123, size=len(content))
        repo = dict(full_name=shared.REPOSITORY, private=False)
        error = HTTPError('https://github.com/test', 504, 'gateway timeout', {}, None)
        with patch.dict('os.environ', {'WSX_PRIVATE_SOURCE': '0'}), \
             patch.object(shared, 'public_json', side_effect=[repo, release, repo, release]), \
             patch.object(shared, 'urlopen', side_effect=[error, io.BytesIO(content)]) as opened:
            self.assertEqual(json.loads(shared.download_index(pin, 'omarchy')), index)
            self.assertEqual(opened.call_args_list[1].args[0].full_url,
                             'https://api.github.com/repos/'+shared.REPOSITORY+'/releases/assets/123')
            self.assertIsNone(opened.call_args_list[1].args[0].get_header('Authorization'))
        index_asset['digest'] = 'sha256:' + '0' * 64
        with patch.dict('os.environ', {'WSX_PRIVATE_SOURCE': '0'}), \
             patch.object(shared, 'public_json', side_effect=[repo, release]), \
             patch.object(shared, 'urlopen', side_effect=error):
            with self.assertRaisesRegex(ValueError, 'metadata differs'):
                shared.download_index(pin, 'omarchy')

    def test_public_download_does_not_fallback_on_not_found(self):
        _, _, pin = self.prepared()
        error = HTTPError('https://github.com/test', 404, 'not found', {}, None)
        with patch.dict('os.environ', {'WSX_PRIVATE_SOURCE': '0'}), \
             patch.object(shared, 'public_json') as metadata, \
             patch.object(shared, 'urlopen', side_effect=error):
            with self.assertRaises(HTTPError):
                shared.download_index(pin, 'omarchy')
            metadata.assert_not_called()

    def test_anonymous_metadata_retries_transient_errors_only(self):
        error = HTTPError('https://api.github.com/test', 504, 'gateway timeout', {}, None)
        with patch.object(shared, 'urlopen', side_effect=[error, io.BytesIO(b'{"ok": true}')]) as opened, \
             patch.object(shared.time, 'sleep') as sleep:
            self.assertEqual(shared.public_json('https://api.github.com/test'), {'ok': True})
            self.assertIsNone(opened.call_args.args[0].get_header('Authorization'))
            sleep.assert_called_once_with(1)
        error = HTTPError('https://api.github.com/test', 404, 'not found', {}, None)
        with patch.object(shared, 'urlopen', side_effect=error) as opened, \
             patch.object(shared.time, 'sleep') as sleep:
            with self.assertRaises(HTTPError):
                shared.public_json('https://api.github.com/test')
            self.assertEqual(opened.call_count, 1)
            sleep.assert_not_called()

    def test_two_image_recipes_share_one_graphics_source_reference(self):
        bundle,index,pin=self.prepared()
        (self.repo/'components/source-delivery.json').write_text(json.dumps(dict(schema_version=1,mode='shared-v2',profiles={'omarchy':pin})))
        (self.repo/'scripts').mkdir();recipe=self.repo/'scripts/image.py'
        indexes=[];recipe_hashes=[]
        with patch.object(delivery,'ROOT',self.repo),patch.object(shared,'download_index',return_value=(bundle/shared.INDEX).read_bytes()),patch.object(delivery.subprocess,'check_output',return_value=b'scripts/image.py\0'):
            for n in (1,2):
                recipe.write_text('revision = '+str(n)+'\n')
                payload=self.root/str(n);payload.mkdir()
                result=delivery.attach_current(self.work,payload)
                sources=dict(component_source=self.receipt,component_source_delivery=result)
                self.assertEqual(delivery.required_assets(payload,sources),list(SHARED_SOURCE_ASSETS))
                self.assertFalse((payload/'component-sources.tar').exists())
                indexes.append(sha(payload/shared.INDEX));recipe_hashes.append(sha(payload/'image-recipe.tar.gz'))
        self.assertEqual(indexes[0],indexes[1]);self.assertNotEqual(recipe_hashes[0],recipe_hashes[1])

    def test_wrong_component_receipt_rejected(self):
        _,index,_=self.prepared()
        receipt=copy.deepcopy(self.receipt);receipt['extra']='different runtime'
        with self.assertRaisesRegex(ValueError,'exact component receipt'):shared.validate_index(index,receipt)

    def test_v2_asset_contract_contains_no_large_component_archive(self):
        m=manifest();m['source_delivery_schema']=2
        self.assertIn('image-recipe.tar.gz',asset_names(m))
        self.assertNotIn('component-sources.tar',asset_names(m))
        self.assertEqual(len(asset_names(m)),8)

    def test_release_review_reads_shared_sources_and_rejects_changed_archive(self):
        import importlib.util
        import shutil
        spec=importlib.util.spec_from_file_location('release_review',Path(__file__).resolve().parents[1]/'scripts/review-release-licenses.py')
        review=importlib.util.module_from_spec(spec);spec.loader.exec_module(review)
        bundle,index,pin=self.prepared()
        (self.repo/'components/source-delivery.json').write_text(json.dumps(dict(schema_version=1,mode='shared-v2',profiles={'omarchy':pin})))
        (self.repo/'scripts').mkdir();(self.repo/'scripts/image.py').write_text('Fixture image recipe')
        payload=self.root/'payload';payload.mkdir()
        with patch.object(delivery,'ROOT',self.repo),patch.object(shared,'download_index',return_value=(bundle/shared.INDEX).read_bytes()),patch.object(delivery.subprocess,'check_output',return_value=b'scripts/image.py\0'):
            result=delivery.attach_current(self.work,payload)
        source=dict(component_source=self.receipt,component_source_delivery=result)
        def fetch(pin,index,destination):
            for name in shared.ARCHIVES: shutil.copy2(bundle/name,destination/name)
        with patch.object(review,'fetch_shared',side_effect=fetch):
            material,hashes,details=review.source_evidence(payload,source,dict(source_delivery_schema=2,distribution_id="wsx-omarchy"))
            self.assertEqual(material['notice_files'],{'LICENSE':sha(self.material/'notices/LICENSE')})
            self.assertTrue(details['public_source_assets_verified'])
            self.assertIn('rootfs-recipe/scripts/image.py',hashes)
            (bundle/shared.ARCHIVES[2]).write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'changed'):
                review.source_evidence(payload,source,dict(source_delivery_schema=2,distribution_id="wsx-omarchy"))
