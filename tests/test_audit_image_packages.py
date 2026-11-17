# SPDX-License-Identifier: GPL-2.0-or-later OR Apache-2.0
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('audit_image_packages', ROOT/'scripts/audit-image-packages.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class PackageAudit(unittest.TestCase):
    def test_actual_package_and_notice_mismatches_are_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root/'sources.json'
            source.write_text(json.dumps({'rootfs_packages': ['example 1-1', 'absent 2-1']}))
            archive = root/'image.tar'
            with tarfile.open(archive, 'w') as tar:
                entries = {
                    'var/lib/pacman/local/example-1-1/desc': b'%NAME%\nexample\n\n%VERSION%\n1-1\n\n%LICENSE%\nMIT\n',
                    'var/lib/pacman/local/example-1-1/files': b'%FILES%\nusr/share/licenses/example/LICENSE\n',
                }
                for name, data in entries.items():
                    info = tarfile.TarInfo(name)
                    info.size = len(data)
                    tar.addfile(info, io.BytesIO(data))
            report = module.audit(archive, source)
            self.assertEqual(report['packages_missing_from_image'], ['absent 2-1'])
            self.assertEqual(report['package_count'], 1)
            self.assertEqual(report['packages'][0]['missing_notice_paths'], ['usr/share/licenses/example/LICENSE'])

    def test_rejects_archive_traversal(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root/'sources.json'
            source.write_text('{"rootfs_packages": []}')
            archive = root/'image.tar'
            with tarfile.open(archive, 'w') as tar:
                tar.addfile(tarfile.TarInfo('../escape'))
            with self.assertRaisesRegex(ValueError, 'Unsafe archive'):
                module.audit(archive, source)


if __name__ == '__main__':
    unittest.main()
