"""Real archive round trips; fixture bytes are not compiler or GPU acceptance."""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT/'scripts'/name)
    mod = importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    return mod
pack = module('package-source-components.py')
admit = module('consume-source-components.py')

@unittest.skipUnless(shutil.which('zstd'), 'zstd CLI required for real archive test')
class Roundtrip(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name);self.work=self.root/'work';self.work.mkdir()
        for folder in ('mesa','venus','kwin-opaque'):
            p=self.work/'private'/folder;p.mkdir(parents=True)
            (p/'fixture').write_bytes(b'component fixture')
        self.receipt=dict(profile='cachyos-plasma',compiled=True,runtime_assembled=True,
            runtime_files={str(p.relative_to(self.work/'private')):admit.sha(p)
                           for p in (self.work/'private').rglob('*') if p.is_file()})
        (self.work/'component-source.json').write_text(json.dumps(self.receipt))
        materials=self.work/'component-materials';(materials/'notices').mkdir(parents=True)
        (materials/'notices/LICENSE-fixture').write_text('Fixture notice; no legal clearance')
        (materials/'sources.tar').write_bytes(b'fixture source archive bytes')
        material_receipt=dict(schema_version=1,collection_complete=True,
            source_receipt_sha256=admit.sha(self.work/'component-source.json'),
            sources=dict(path='sources.tar',sha256=admit.sha(materials/'sources.tar'),size=(materials/'sources.tar').stat().st_size),
            notice_files={'LICENSE-fixture':admit.sha(materials/'notices/LICENSE-fixture')})
        (materials/'materials.json').write_text(json.dumps(material_receipt))
        self.bundle=self.root/'bundle';pack.package(self.work,self.bundle)
        self.manifest=json.loads((self.bundle/'manifest.json').read_text())
    def consume(self,profile='cachyos-plasma',digest=None):
        admit.consume(self.bundle,self.root/'admitted',profile,digest or self.manifest['sha256'])
    def test_roundtrip(self):
        self.consume()
        self.assertEqual(json.loads((self.root/'admitted/component-source.json').read_text()),self.receipt)
    def test_wrong_profile(self):
        with self.assertRaisesRegex(ValueError,'identity'):self.consume('omarchy')
    def test_wrong_pin(self):
        with self.assertRaisesRegex(ValueError,'digest'):self.consume(digest='0'*64)
    def test_corrupt_archive(self):
        with (self.bundle/self.manifest['archive']).open('ab') as stream:stream.write(b'corruption')
        with self.assertRaisesRegex(ValueError,'digest'):self.consume()
    def test_changed_receipt(self):
        self.manifest['source_receipt']['compiled']=False
        (self.bundle/'manifest.json').write_text(json.dumps(self.manifest))
        with self.assertRaisesRegex(ValueError,'receipt'):self.consume()
    def test_no_overwrite(self):
        (self.root/'admitted').mkdir()
        with self.assertRaisesRegex(ValueError,'Fresh'):self.consume()
    def test_postbuild_corruption(self):
        (self.work/'private/mesa/fixture').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'changed'):pack.package(self.work,self.root/'bad')

    def test_changed_source_sidecar_is_rejected(self):
        (self.bundle/'sources.tar').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'Source materials'):
            self.consume()
    def test_missing_notice_materials_blocks_packaging(self):
        (self.work/'component-materials/notices/LICENSE-fixture').unlink()
        with self.assertRaisesRegex(ValueError,'Notice materials changed'):
            pack.package(self.work,self.root/'missing-notices')
