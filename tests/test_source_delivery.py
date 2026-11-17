"""Require runtime/source pairing before any network publication begins."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
import tarfile
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from source_delivery import attach, required_assets
from component_materials import sha
import source_delivery


class Delivery(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.work = Path(temp.name); self.payload = self.work/'payload'; self.payload.mkdir()
        self.receipt = dict(origin='source-build', profile='cachyos-plasma')
        (self.work/'component-source.json').write_text(json.dumps(self.receipt))
        material = self.work/'component-materials'; (material/'notices').mkdir(parents=True)
        (material/'notices/NOTICE').write_text('Fixture')
        with tarfile.open(material/'sources.tar', 'w'):
            pass
        report = dict(schema_version=1, collection_complete=True, source_entries=[],
            source_receipt_sha256=sha(self.work/'component-source.json'),
            sources=dict(path='sources.tar', sha256=sha(material/'sources.tar'), size=(material/'sources.tar').stat().st_size),
            notice_files={'NOTICE': sha(material/'notices/NOTICE')})
        (material/'materials.json').write_text(json.dumps(report))
        self.sources = dict(component_source=self.receipt,
                            component_source_delivery=attach(self.work, self.payload))

    def test_pairing_without_legal_clearance(self):
        self.assertEqual(len(required_assets(self.payload, self.sources)), 3)
        self.assertFalse(self.sources['component_source_delivery']['corresponding_source_complete'])

    def test_missing_source_blocks(self):
        (self.payload/'component-sources.tar').unlink()
        with self.assertRaisesRegex(ValueError, 'Missing regular source'):
            required_assets(self.payload, self.sources)

    def test_corrupt_source_blocks(self):
        (self.payload/'component-sources.tar').write_bytes(b'corrupted')
        with self.assertRaisesRegex(ValueError, 'Source asset changed'):
            required_assets(self.payload, self.sources)

    def test_source_build_cannot_omit_delivery(self):
        del self.sources['component_source_delivery']
        with self.assertRaisesRegex(ValueError, 'requires paired'):
            required_assets(self.payload, self.sources)

    def test_different_runtime_receipt_blocks(self):
        self.sources['component_source'] = dict(origin='source-build', profile='different')
        with self.assertRaisesRegex(ValueError, 'receipt mismatch'):
            required_assets(self.payload, self.sources)

    def test_reuse_retains_current_recipe_without_mutating_component_sources(self):
        material=self.work/'component-materials'
        with tarfile.open(material/'sources.tar','w'):
            pass
        report=json.loads((material/'materials.json').read_text())
        report['source_entries']=[]
        report['sources'].update(sha256=sha(material/'sources.tar'),size=(material/'sources.tar').stat().st_size)
        (material/'materials.json').write_text(json.dumps(report))
        original=sha(material/'sources.tar')
        (self.work/'component-reuse.json').write_text('{"rebuilt": false}\n')
        repo=self.work/'repo';(repo/'scripts').mkdir(parents=True)
        (repo/'scripts/assemble.py').write_text('# Current rootfs assembly\n')
        (repo/'docs').mkdir()
        (repo/'docs/private-prereleases.md').write_text('Private delivery authorization fixture\n')
        payload=self.work/'second-payload';payload.mkdir()
        with patch.object(source_delivery,'ROOT',repo),patch.object(source_delivery.subprocess,'check_output',return_value=b'scripts/assemble.py\0docs/private-prereleases.md\0') as selection:
            delivery=attach(self.work,payload)
        self.assertIn('docs/private-prereleases.md', selection.call_args.args[0])
        self.assertEqual(sha(material/'sources.tar'),original)
        self.assertEqual(len(required_assets(payload,dict(component_source=self.receipt,component_source_delivery=delivery))),3)
        with tarfile.open(payload/'component-sources.tar') as archive:
            self.assertEqual(archive.extractfile('rootfs-recipe/scripts/assemble.py').read(),b'# Current rootfs assembly\n')
            self.assertIn('rootfs-recipe/original-component-materials.json',archive.getnames())
            self.assertEqual(archive.extractfile('rootfs-recipe/docs/private-prereleases.md').read(),
                             b'Private delivery authorization fixture\n')


class OmarchyProjection(unittest.TestCase):
    def test_projection_preserves_other_sources_and_rejects_unreviewed_bytes(self):
        import io
        import hashlib
        with tempfile.TemporaryDirectory() as temporary:
            payload = Path(temporary)
            name = next(iter(source_delivery.RETIRED_INPUTS))
            data = b'Reviewed retired fixture'
            self.addCleanup(patch.stopall)
            patch.object(source_delivery, 'RETIRED_INPUTS', {name: hashlib.sha256(data).hexdigest()}).start()
            archive_path = payload/'component-sources.tar'
            def fixture(content, record=True):
                entries = []
                with tarfile.open(archive_path, 'w') as archive:
                    for path, value in [('recipe/'+name, content), ('upstream/COPYING', b'Keep upstream license')]:
                        info = tarfile.TarInfo(path); info.size = len(value)
                        archive.addfile(info, io.BytesIO(value))
                        entries.append(dict(path=path, size=len(value), sha256=hashlib.sha256(value).hexdigest()))
                report = dict(sources=dict(sha256=sha(archive_path), size=archive_path.stat().st_size),
                              source_entries=entries if record else entries[1:])
                (payload/'component-materials.json').write_text(json.dumps(report))
            fixture(data)
            original = sha(archive_path)
            source_delivery.project_sources(payload, 'omarchy')
            with tarfile.open(archive_path) as archive:
                self.assertEqual(archive.getnames(), ['upstream/COPYING'])
                self.assertEqual(archive.extractfile('upstream/COPYING').read(), b'Keep upstream license')
            report = json.loads((payload/'component-materials.json').read_text())
            self.assertEqual(report['source_projection']['original_sources']['sha256'], original)
            self.assertEqual(len(report['source_projection']['excluded']), 1)
            for content, record, message in [(b'Changed', True, 'differs from reviewed'),
                                              (data, False, 'recorded entry')]:
                fixture(content, record)
                before = sha(archive_path)
                with self.assertRaisesRegex(ValueError, message):
                    source_delivery.project_sources(payload, 'omarchy')
                self.assertEqual(sha(archive_path), before)
