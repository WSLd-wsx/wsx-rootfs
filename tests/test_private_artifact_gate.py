"""Private upload approval is distinct from source grants and public clearance."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import tarfile
import unittest
from test_contract import manifest
from source_delivery import attach
from license_fixture import seed

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
spec=importlib.util.spec_from_file_location('private_gate',ROOT/'scripts/private-artifact-gate.py')
gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)


class PrivateGateTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.root=Path(temp.name)

    def test_public_wrong_or_unknown_privacy_rejected(self):
        gate.require_private(gate.REPOSITORY,dict(full_name=gate.REPOSITORY,private=True))
        for metadata in [dict(full_name=gate.REPOSITORY,private=False),dict(full_name=gate.REPOSITORY),
                         dict(full_name='other/repo',private=True)]:
            with self.assertRaisesRegex(ValueError,'approved private'):
                gate.require_private(gate.REPOSITORY,metadata)
        with self.assertRaises(ValueError):
            gate.require_private('other/repo',dict(full_name='other/repo',private=True))

    def test_active_matching_source_policy_required(self):
        seed(self.root)
        path=self.root/'docs/licensing/modules.json'
        policy=json.loads(path.read_text())
        policy.update(license_grant=True,private_artifacts_allowed=True,
                      activation=dict(approved_by='WGY (GitHub: wgy-wsx) <wgy@wsxdesk.com>'))
        policy['license_selection']['effective']=True
        path.write_text(json.dumps(policy))
        mapping=dict(license_grant=True,private_artifacts_allowed=True,
                     policy_files={n:gate.sha(self.root/n) for n in gate.license_paths(self.root)})
        gate.require_policy(self.root,mapping)
        inactive=copy.deepcopy(mapping);inactive['license_grant']=False
        with self.assertRaisesRegex(ValueError,'Effective'):
            gate.require_policy(self.root,inactive)
        (self.root/'LICENSE').write_text('changed license')
        with self.assertRaisesRegex(ValueError,'current active'):
            gate.require_policy(self.root,mapping)

    def materials(self):
        work=self.root/'work';folder=work/'component-materials';(folder/'notices').mkdir(parents=True)
        receipt=dict(origin='source-build',profile='omarchy',compiled=True,runtime_assembled=True)
        (work/'component-source.json').write_text(json.dumps(receipt))
        with tarfile.open(folder/'sources.tar', 'w'):
            pass
        (folder/'notices/LICENSE').write_text('Fixture notice')
        report=dict(schema_version=1,collection_complete=True,source_entries=[],source_receipt_sha256=gate.sha(work/'component-source.json'),
                    sources=dict(path='sources.tar',sha256=gate.sha(folder/'sources.tar'),size=(folder/'sources.tar').stat().st_size),
                    notice_files={'LICENSE':gate.sha(folder/'notices/LICENSE')})
        (folder/'materials.json').write_text(json.dumps(report))
        return work,receipt,report

    def test_component_source_and_binary_pair_verified(self):
        work,receipt,report=self.materials();package=work/'packages';package.mkdir()
        archive=package/'fixture.tar.zst';archive.write_bytes(b'fixture binary')
        for name in ('materials.json','sources.tar'):
            (package/name).write_bytes((work/'component-materials'/name).read_bytes())
        item=dict(origin='source-build',profile='omarchy',source_receipt=receipt,archive=archive.name,
                  sha256=gate.sha(archive),size=archive.stat().st_size,materials_sha256=gate.sha(package/'materials.json'),
                  source_materials=report['sources'])
        (package/'manifest.json').write_text(json.dumps(item))
        names=[archive.name,'sources.tar','materials.json','manifest.json']
        (package/'SHA256SUMS').write_text(''.join(f'{gate.sha(package/n)}  {n}\n' for n in names))
        gate.verify_component(work)
        (package/'sources.tar').write_bytes(b'changed source')
        with self.assertRaisesRegex(ValueError,'checksum'):
            gate.verify_component(work)

    def test_rootfs_source_pair_and_offline_result_required(self):
        work,receipt,report=self.materials();payload=work/'payload';payload.mkdir()
        item=manifest();item['source_delivery_schema']=1
        (payload/item['asset_name']).write_bytes(b'fixture rootfs')
        item.update(sha256=gate.sha(payload/item['asset_name']),compressed_size=(payload/item['asset_name']).stat().st_size)
        (payload/'manifest.json').write_text(json.dumps(item))
        (payload/'sources.json').write_text(json.dumps(dict(component_source=receipt,component_source_delivery=attach(work,payload))))
        validation=payload/'validation.json';validation.write_text('{"offline":"passed"}')
        def sums():
            (payload/'SHA256SUMS').write_text(''.join(f'{gate.sha(payload/n)}  {n}\n' for n in gate.asset_names(item) if n!='SHA256SUMS'))
        sums();gate.verify_rootfs(work)
        validation.write_text('{"offline":"failed"}');sums()
        with self.assertRaisesRegex(ValueError,'offline'):
            gate.verify_rootfs(work)
        validation.write_text('{"offline":"passed"}');sums()
        (payload/'component-sources.tar').unlink()
        with self.assertRaisesRegex(ValueError,'Missing/unsafe'):
            gate.verify_rootfs(work)

    def test_extra_files_cannot_hitchhike_in_upload(self):
        (self.root/'data').write_bytes(b'fixture')
        (self.root/'SHA256SUMS').write_text(f'{gate.sha(self.root/"data")}  data\n')
        gate.verify_files(self.root,['data','SHA256SUMS'])
        (self.root/'extra').write_text('not declared')
        with self.assertRaisesRegex(ValueError,'Unexpected'):
            gate.verify_files(self.root,['data','SHA256SUMS'])
