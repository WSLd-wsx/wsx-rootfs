import sys
import tempfile
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from image_paths import resolve


class ImagePathTests(unittest.TestCase):
    def test_absolute_link_resolves_inside_image(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'link').symlink_to('/usr/bin/tool')
            self.assertEqual(resolve(root,'link'),root/'usr/bin/tool')

    def test_loop_rejects(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'a').symlink_to('b');(root/'b').symlink_to('a')
            with self.assertRaises(ValueError):resolve(root,'a')

    def test_host_mount_link_rejects(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'link').symlink_to('/mnt/c/WSX/runtime')
            with self.assertRaises(ValueError):resolve(root,'link')
