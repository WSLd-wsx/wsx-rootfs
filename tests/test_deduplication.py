"""Simulated completed/partial-release admission; no API calls or builds."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from test_contract import manifest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from contract import identity
spec=importlib.util.spec_from_file_location('prepare_build',Path(__file__).resolve().parents[1]/'scripts/prepare-build.py')
prepare=importlib.util.module_from_spec(spec);spec.loader.exec_module(prepare)


class DeduplicationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.output=Path(self.temp.name)/'build.json'
        self.inputs=dict(distribution_id='wsx-omarchy',architecture='x86_64',wsx_revision=1,
                        upstream_release='v4.0.6',upstream_commit='a'*40,recipe_files={})
        self.build_id=identity(self.inputs)
        self.m=manifest();self.m['build_identity']=self.build_id
        names=[self.m['asset_name'],'manifest.json','sources.json','validation.json','SHA256SUMS']
        self.marker=dict(schema_version=1,build_identity=self.build_id,
                         assets={n:dict(size=1,sha256='0'*64) for n in names})
        self.marker['assets'][self.m['asset_name']]=dict(size=self.m['compressed_size'],sha256=self.m['sha256'])
        self.documents={'manifest.json':self.m,'completion.json':self.marker}
        self.release=dict(id=1,tag_name='wsx-omarchy-4.0.6-r1',draft=True,prerelease=False)
        def command(argv,**kwargs):
            if argv[0]=='python3':return json.dumps(dict(upstream_release='v4.0.6',upstream_commit='a'*40))
            if argv[1]=='ls-files':return b''
            if argv[1]=='rev-parse':return 'd'*40
            raise AssertionError(argv)
        def download(repo,asset,path):path.write_text(json.dumps(self.documents[asset['name']]))
        for name,value in [('releases',lambda repo:[self.release]),
                           ('api',lambda path:[dict(name=n,id=n) for n in self.documents]),
                           ('download',download)]:
            mock=patch.object(prepare,name,value);mock.start();self.addCleanup(mock.stop)
        for mock in [patch.object(prepare.subprocess,'check_output',command),
                     patch.object(sys,'argv',['prepare-build.py','--repo','fixture/rootfs','--revision','1','--output',str(self.output)])]:
            mock.start();self.addCleanup(mock.stop)
        self.remote=patch.object(prepare,'verify_remote');self.verify=self.remote.start();self.addCleanup(self.remote.stop)

    def test_complete_draft_and_public_deduplicate(self):
        for draft in (True,False):
            self.release['draft']=draft;prepare.main()
            self.assertTrue(json.loads(self.output.read_text())['completed'])
        self.assertEqual(self.verify.call_count,2)

    def test_partial_draft_retries(self):
        del self.documents['completion.json'];prepare.main()
        self.assertFalse(json.loads(self.output.read_text())['completed'])
        self.verify.assert_not_called()

    def test_incomplete_public_refuses_repair(self):
        del self.documents['completion.json'];self.release['draft']=False
        with self.assertRaises(ValueError):prepare.main()

    def test_changed_inputs_require_revision(self):
        self.m['build_identity']='f'*64
        with self.assertRaises(ValueError):prepare.main()

    def test_missing_required_asset_is_not_complete(self):
        del self.marker['assets']['sources.json']
        with self.assertRaises(ValueError):prepare.main()
        self.verify.assert_not_called()

    def test_failed_remote_verification_is_not_complete(self):
        self.verify.side_effect=ValueError('Remote hash mismatch')
        with self.assertRaises(ValueError):prepare.main()
        self.assertFalse(self.output.exists())

    def test_source_paired_payload_deduplicates(self):
        from payload_contract import SOURCE_ASSETS
        self.m['source_delivery_schema'] = 1
        self.marker['assets'].update({name: dict(size=1, sha256='1'*64) for name in SOURCE_ASSETS})
        prepare.main()
        self.assertTrue(json.loads(self.output.read_text())['completed'])
        self.verify.assert_called_once()

    def test_source_paired_payload_cannot_drop_any_sidecar(self):
        from payload_contract import SOURCE_ASSETS
        self.m['source_delivery_schema'] = 1
        for missing in SOURCE_ASSETS:
            self.marker['assets'].update({name: dict(size=1, sha256='1'*64) for name in SOURCE_ASSETS})
            del self.marker['assets'][missing]
            with self.subTest(missing=missing), self.assertRaises(ValueError):
                prepare.main()
        self.verify.assert_not_called()

class CachyosSourceDeduplicationTests(unittest.TestCase):
    def test_complete_and_missing_source_assets(self):
        import runpy
        import release_access
        from payload_contract import asset_names
        root=Path(__file__).resolve().parents[1]
        lock=json.loads((root/'distros/cachyos-plasma/upstream/source.json').read_text())
        inputs=dict(distribution_id='wsx-cachyos-plasma',architecture='x86_64',wsx_revision=1,
            snapshot='2026.11.1',installer_commit=lock['commit'],
            snapshot_kind='explicit-wsx-build-date-not-upstream-release',recipe_files={})
        build_id=identity(inputs)
        m=manifest('2026.11.1-r1','wsx-cachyos-plasma')
        m.update(build_identity=build_id,source_delivery_schema=1,cpu_requirements={'architecture_level':'x86-64-v3'})
        marker=dict(schema_version=1,build_identity=build_id,
            assets={n:dict(size=1,sha256='0'*64) for n in asset_names(m)})
        marker['assets'][m['asset_name']]=dict(size=m['compressed_size'],sha256=m['sha256'])
        documents={'manifest.json':m,'completion.json':marker}
        release=dict(id=1,tag_name='wsx-cachyos-plasma-2026.11.1-r1',draft=True,prerelease=False)
        def command(argv,**kwargs):
            if argv[1]=='ls-files':return b''
            if argv[1]=='rev-parse':return 'd'*40
            raise AssertionError(argv)
        with tempfile.TemporaryDirectory() as temp:
            output=Path(temp)/'build.json'
            with patch.object(sys,'argv',['prepare-cachyos.py','--snapshot','2026.11.1','--revision','1','--repo','fixture/rootfs','--output',str(output)]), \
                 patch.object(prepare.subprocess,'check_output',command), \
                 patch.object(release_access,'releases',return_value=[release]), \
                 patch.object(release_access,'api',return_value=[dict(name=n,id=n) for n in documents]), \
                 patch.object(release_access,'download',side_effect=lambda repo,asset,path:path.write_text(json.dumps(documents[asset['name']]))), \
                 patch.object(release_access,'verify_remote') as verify:
                runpy.run_path(str(root/'scripts/prepare-cachyos.py'),run_name='__main__')
                self.assertTrue(json.loads(output.read_text())['completed'])
                verify.assert_called_once();verify.reset_mock()
                del marker['assets']['component-sources.tar']
                with self.assertRaisesRegex(ValueError,'Incomplete completion'):
                    runpy.run_path(str(root/'scripts/prepare-cachyos.py'),run_name='__main__')
                verify.assert_not_called()
