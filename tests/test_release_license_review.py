"""Archive inspection rejects ambiguous paths and resolves hardlink evidence."""
import importlib.util
import io
from pathlib import Path
import tarfile
import unittest

spec = importlib.util.spec_from_file_location('release_review', Path(__file__).resolve().parents[1]/'scripts/review-release-licenses.py')
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


def archive(entries):
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode='w') as tar:
        for name, target in entries:
            info = tarfile.TarInfo(name)
            if target is not None:
                info.type = tarfile.LNKTYPE
                info.linkname = target
                tar.addfile(info)
            else:
                info.size = 7
                tar.addfile(info, io.BytesIO(b'license'))
    output.seek(0)
    return output


class ArchiveReviewTests(unittest.TestCase):
    def test_notice_hardlink(self):
        hashes, _, texts, _ = review.members(archive([
            ('usr/share/licenses/a/LICENSE', None),
            ('usr/share/licenses/b/LICENSE', 'usr/share/licenses/a/LICENSE')]))
        self.assertEqual(len(hashes), 2)
        self.assertEqual(texts['usr/share/licenses/b/LICENSE'], b'license')

    def test_duplicate_normalized_path(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            review.members(archive([('./x', None), ('x', None)]))

    def test_path_escape(self):
        with self.assertRaisesRegex(ValueError, 'Unsafe'):
            review.members(archive([('../outside', None)]))

    def test_unresolved_hardlink(self):
        with self.assertRaisesRegex(ValueError, 'Unresolved'):
            review.members(archive([('x', 'missing')]))

    def test_omarchy_notice_capture(self):
        _, _, texts, _ = review.members(archive([('usr/share/omarchy/LICENSE', None)]))
        self.assertEqual(texts['usr/share/omarchy/LICENSE'], b'license')

    def test_output_schema_uses_license_treatment(self):
        import json
        root = Path(__file__).resolve().parents[1]
        for output in json.loads((root/'components/license-boundaries.json').read_text())['outputs']:
            self.assertIsInstance(output['license_treatment'], str)

    def test_image_named_notice_is_not_license_text(self):
        self.assertFalse(review.upstream_text_candidate('usr/share/omarchy/manual/images/notice-weather.webp'))
        self.assertTrue(review.upstream_text_candidate('usr/share/omarchy/default/fonts/omarchy/README.md'))

    def test_missing_owned_notice_is_reported(self):
        texts = {'var/lib/pacman/local/example-1/desc': b'%NAME%\nexample\n\n%VERSION%\n1\n\n%LICENSE%\nMIT\n',
                 'var/lib/pacman/local/example-1/files': b'%FILES%\nusr/share/licenses/example/LICENSE\n'}
        evidence = review.whole_image_evidence({}, {}, texts)
        self.assertEqual(evidence['packages'][0]['missing_owned_notices'], ['usr/share/licenses/example/LICENSE'])

    def test_duplicate_package_field_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            review.pacman_fields(b'%NAME%\na\n%NAME%\nb\n')

    def test_cachyos_requires_kwin_original_prepared_sources_and_notices(self):
        import copy
        index=dict(profile='cachyos-plasma',component_receipt=dict(archives={'kwin':{'sha256':'a'*64}}),files=[dict(entries=[
            dict(path='archives/kwin.archive',sha256='a'*64),
            dict(path='build-materials/kwin/prepared/source.cpp',sha256='b'*64),
            dict(path='notices/upstream/kwin/COPYING',sha256='c'*64)])])
        manifest=dict(distribution_id='wsx-cachyos-plasma')
        review.check_profile_sources(index,manifest)
        for i in range(3):
            broken=copy.deepcopy(index);del broken['files'][0]['entries'][i]
            with self.assertRaises(ValueError): review.check_profile_sources(broken,manifest)
        with self.assertRaises(ValueError): review.check_profile_sources(index,dict(distribution_id='wsx-omarchy'))

    def test_regenerated_notices_bound_to_validated_recipe_inventory(self):
        base='rootfs-recipe/image-materials/component-materials/notices/'
        original={'MODULE-LICENSES.json':'old','MODULE-NOTICES.txt':'old2','MIT.txt':'retained'}
        rows=[dict(path=base+'MODULE-LICENSES.json',sha256='new'),dict(path=base+'MODULE-NOTICES.txt',sha256='new2')]
        source=dict(component_source_delivery=dict(recipe_entries=rows))
        expected=review.expected_image_notices(None,source,original)
        self.assertEqual(expected,{'MODULE-LICENSES.json':'new','MODULE-NOTICES.txt':'new2','MIT.txt':'retained'})
        self.assertEqual(original['MODULE-LICENSES.json'],'old')
        source['component_source_delivery']['recipe_entries']=rows[:1]
        with self.assertRaises(ValueError): review.expected_image_notices(None,source,original)
