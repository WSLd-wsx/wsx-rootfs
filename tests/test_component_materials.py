"""Source evidence integrity is separate from distribution clearance."""
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import component_materials as materials
from license_inputs import paths as license_paths
from license_fixture import seed


class MaterialsTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.work = self.root / 'work'
        (self.work / 'source-archives').mkdir(parents=True)
        seed(self.root)
        archive = self.work / 'source-archives/example.archive'
        with tarfile.open(archive, 'w') as tar:
            data = b'upstream notice\n'
            info = tarfile.TarInfo('example/LICENSE'); info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
        receipt = dict(origin='source-build', compiled=True,
                       archives={'example': {'sha256': materials.sha(archive)}},
                       recipe_files={n:materials.sha(self.root/n) for n in license_paths(self.root)+['recipe.py','vendor/example.c']})
        (self.work / 'component-source.json').write_text(json.dumps(receipt))
        for name in ('build-packages.txt', 'build-repositories.conf'):
            (self.work / name).write_text('fixture\n')
        mock = patch.object(materials, 'ROOT', self.root)
        mock.start(); self.addCleanup(mock.stop)

    def test_retains_sources_and_notices_without_grant(self):
        report = materials.prepare_legacy(self.work)
        self.assertEqual(materials.verify(self.work), report)
        self.assertFalse(report['distribution_allowed'])
        self.assertFalse(report['corresponding_source_complete'])
        self.assertIn('upstream/example/example/LICENSE', report['notice_files'])
        with tarfile.open(self.work / 'component-materials/sources.tar') as archive:
            self.assertIn('recipe/recipe.py', archive.getnames())
            self.assertIn('archives/example.archive', archive.getnames())
            self.assertIn('licensing/MODULE-LICENSES.json', archive.getnames())
            self.assertIn('licensing/MODULE-NOTICES.txt', archive.getnames())
        mapping=json.loads((self.work/'component-materials/notices/MODULE-LICENSES.json').read_text())
        self.assertFalse(mapping['license_grant'])
        self.assertEqual(mapping['outputs'][0]['inventoried_sources'], ['vendor/example.c'])

    def test_changed_notice_rejected(self):
        materials.prepare_legacy(self.work)
        (self.work / 'component-materials/notices/README.txt').write_text('changed')
        with self.assertRaisesRegex(ValueError, 'Notice materials changed'):
            materials.verify(self.work)

    def test_collection_cannot_complete_with_omitted_build_dependency(self):
        (self.root/'helper.py').write_text('# Required fixture helper\n')
        (self.root/'recipe.py').write_text('import helper\n')
        receipt_path=self.work/'component-source.json'
        receipt=json.loads(receipt_path.read_text())
        receipt['recipe_files']['recipe.py']=materials.sha(self.root/'recipe.py')
        receipt_path.write_text(json.dumps(receipt))
        with self.assertRaisesRegex(ValueError,'Required source absent.*helper.py'):
            materials.prepare_legacy(self.work)
        self.assertFalse((self.work/'component-materials/materials.json').exists())

    def test_source_archive_tampering_rejected(self):
        (self.work / 'source-archives/example.archive').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'Source archive changed'):
            materials.prepare_legacy(self.work)

    def test_notice_symlink_rejected(self):
        materials.prepare_legacy(self.work)
        (self.work / 'component-materials/notices/link').symlink_to(self.root / 'recipe.py')
        with self.assertRaisesRegex(ValueError, 'symlinks'):
            materials.verify(self.work)
