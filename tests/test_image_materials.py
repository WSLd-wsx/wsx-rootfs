"""Image source snapshots retain immutable compilation evidence."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import image_materials as image
import product_licenses as product
from license_fixture import seed
from license_inputs import paths


class ImageMaterialsTests(unittest.TestCase):
    def test_image_snapshot_is_not_compilation_and_detects_source_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'repo';root.mkdir();seed(root)
            work=Path(tmp)/'work';notices=work/'component-materials/notices';notices.mkdir(parents=True)
            names=paths(root)+['recipe.py','vendor/example.c']
            receipt=dict(profile='omarchy',compiled=True,recipe_files={n:product.sha(root/n) for n in names},runtime_files={})
            (work/'component-source.json').write_text(json.dumps(receipt))
            product.write_component_map(root,receipt,notices)
            original={p.name:p.read_bytes() for p in notices.iterdir() if p.is_file()}
            (root/'recipe.py').write_text('# New image assembly logic\n')
            with patch.object(image.subprocess,'check_output',return_value=('\0'.join(names)+'\0').encode()):
                snapshot=image.image_snapshot(root,work)
            self.assertFalse(snapshot['compiled'])
            self.assertEqual(snapshot['origin'],'image-assembly-source-snapshot')
            self.assertEqual(original,{p.name:p.read_bytes() for p in notices.iterdir() if p.is_file()})
            self.assertEqual(json.loads((work/'component-source.json').read_text()),receipt)
            self.assertEqual(image.verify_image_snapshot(root,work),snapshot)
            (root/'recipe.py').write_text('# Tampered after assembly\n')
            with self.assertRaisesRegex(ValueError,'changed after snapshot'):
                image.verify_image_snapshot(root,work)
