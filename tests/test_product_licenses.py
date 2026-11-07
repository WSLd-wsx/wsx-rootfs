"""Concrete product provenance and reconstruction dependencies, not legal verdicts."""
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import product_licenses as product
from license_inputs import paths as license_paths
from license_fixture import seed


class ProductLicenses(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)/'repo';self.root.mkdir();seed(self.root)
        self.work=Path(temp.name)/'work';self.notices=self.work/'component-materials/notices';self.notices.mkdir(parents=True)
        self.receipt=dict(profile='omarchy', recipe_files={n:product.sha(self.root/n)
            for n in license_paths(self.root)+['recipe.py','vendor/example.c']})

    def test_policy_changes_after_build_rejected(self):
        (self.root/'docs/licensing/modules.json').write_text('{}')
        with self.assertRaises((ValueError,KeyError)):
            product.write_component_map(self.root,self.receipt,self.notices)

    def test_discovered_local_import_cannot_remain_restricted(self):
        (self.root/'restricted.py').write_text('pass\n')
        (self.root/'recipe.py').write_text('import restricted\n')
        with self.assertRaisesRegex(ValueError,'PolyForm scope'):
            product.check_boundaries(self.root)

    def test_product_map_binds_existing_rule_without_grant(self):
        result=product.write_component_map(self.root,self.receipt,self.notices)
        self.assertFalse(result['license_grant'])
        self.assertEqual(result['source_files']['vendor/example.c']['existing_rule'],'fixture')
        self.assertEqual(result['outputs'][0]['inventoried_sources'],['vendor/example.c'])

    def test_required_import_missing_from_receipt_is_rejected(self):
        (self.root/'helper.py').write_text('pass\n')
        (self.root/'recipe.py').write_text('import helper\n')
        self.receipt['recipe_files']['recipe.py']=product.sha(self.root/'recipe.py')
        with self.assertRaisesRegex(ValueError,'Required source absent.*helper.py'):
            product.write_component_map(self.root,self.receipt,self.notices)

    def test_changed_required_source_is_rejected(self):
        (self.root/'recipe.py').write_text('# changed after compilation\n')
        with self.assertRaisesRegex(ValueError,'Required source absent or changed'):
            product.write_component_map(self.root,self.receipt,self.notices)

    def test_partial_output_source_set_is_rejected(self):
        policy=self.root/'components/license-boundaries.json'
        boundary=json.loads(policy.read_text())
        boundary['outputs'][0]['source_paths']=['vendor/*']
        policy.write_text(json.dumps(boundary))
        self.receipt['recipe_files'][str(policy.relative_to(self.root))]=product.sha(policy)
        (self.root/'vendor/omitted.c').write_text('/* omitted */\n')
        with self.assertRaisesRegex(ValueError,'Output source absent.*omitted.c'):
            product.write_component_map(self.root,self.receipt,self.notices)

    def test_installed_input_missing_from_receipt_is_rejected(self):
        policy=self.root/'components/license-boundaries.json'
        boundary=json.loads(policy.read_text())
        boundary['installed_inputs']={'recipe.py':['installed.sh']}
        policy.write_text(json.dumps(boundary))
        self.receipt['recipe_files'][str(policy.relative_to(self.root))]=product.sha(policy)
        (self.root/'installed.sh').write_text('# fixture\n')
        with self.assertRaisesRegex(ValueError,'Required source absent.*installed.sh'):
            product.write_component_map(self.root,self.receipt,self.notices)

    def test_actual_installed_hashes_and_missing_output(self):
        product.write_component_map(self.root,self.receipt,self.notices)
        rootfs=self.work/'rootfs';target=rootfs/'usr/share/licenses/wsx-components'
        shutil.copytree(self.notices,target)
        with self.assertRaisesRegex(ValueError,'missing'):
            product.write_image_map(rootfs,self.work)
        (rootfs/'usr/bin').mkdir(parents=True);(rootfs/'usr/bin/fixture').write_bytes(b'compiled fixture')
        result=product.write_image_map(rootfs,self.work)
        self.assertEqual(result['files'][0]['sha256'],product.sha(rootfs/'usr/bin/fixture'))
        product.verify_image_map(rootfs,self.work)
        (rootfs/'usr/bin/fixture').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'binding changed'):
            product.verify_image_map(rootfs,self.work)

    def test_notice_tampering_rejected(self):
        product.write_component_map(self.root,self.receipt,self.notices)
        rootfs=self.work/'rootfs';target=rootfs/'usr/share/licenses/wsx-components'
        shutil.copytree(self.notices,target);(target/'MODULE-NOTICES.txt').write_text('changed')
        with self.assertRaisesRegex(ValueError,'differs'):
            product.write_image_map(rootfs,self.work)

    def test_package_metadata_and_notices_are_bound_without_clearance(self):
        product.write_component_map(self.root,self.receipt,self.notices)
        rootfs=self.work/'rootfs'
        shutil.copytree(self.notices,rootfs/'usr/share/licenses/wsx-components')
        (rootfs/'usr/bin').mkdir(parents=True)
        (rootfs/'usr/bin/fixture').write_bytes(b'fixture')
        package=rootfs/'var/lib/pacman/local/example-1.0-1'
        package.mkdir(parents=True)
        (package/'desc').write_text('%NAME%\nexample\n\n%VERSION%\n1.0-1\n\n%LICENSE%\ncustom\nMIT\n')
        (package/'files').write_text('%FILES%\nusr/bin/example\n')
        notice=rootfs/'usr/share/licenses/example/LICENSE'
        notice.parent.mkdir();notice.write_text('Retained upstream notice')
        report=product.write_image_map(rootfs,self.work)
        evidence=report['package_evidence']
        self.assertTrue(evidence['evidence_present'])
        self.assertFalse(evidence['distribution_allowed'])
        self.assertEqual(evidence['packages'][0]['declared_licenses'],['custom','MIT'])
        product.verify_image_map(rootfs,self.work)
        notice.write_text('Changed notice')
        with self.assertRaisesRegex(ValueError,'binding changed'):
            product.verify_image_map(rootfs,self.work)

    def test_package_evidence_rejects_links_and_malformed_identity(self):
        rootfs=self.work/'rootfs';package=rootfs/'var/lib/pacman/local/example'
        package.mkdir(parents=True)
        (package/'files').write_text('%FILES%\n')
        (package/'desc').write_text('%NAME%\nexample\n')
        with self.assertRaisesRegex(ValueError,'VERSION'):
            product.package_evidence(rootfs)
        (package/'desc').unlink()
        (package/'desc').symlink_to(self.root/'recipe.py')
        with self.assertRaisesRegex(ValueError,'Unsafe package'):
            product.package_evidence(rootfs)

    def test_empty_package_database_is_not_review_completion(self):
        result=product.package_evidence(self.root)
        self.assertFalse(result['evidence_present'])
        self.assertFalse(result['distribution_allowed'])
        self.assertEqual(result['license_review'],'pending')

    def test_real_reconstruction_graph_has_no_polyform_default(self):
        closures=product.check_boundaries(Path(__file__).resolve().parents[1])
        self.assertIn('scripts/build-kwin.py',closures['kwin-module-rebuild']['files'])
        self.assertIn('scripts/component_materials.py',closures['paired-component-build']['files'])

    def test_actual_repository_policies_map_both_output_profiles(self):
        root=Path(__file__).resolve().parents[1]
        names=set(license_paths(root))
        for directory in ('vendor','scripts','components','distros','guest','schema','.github/workflows'):
            names.update(str(p.relative_to(root)) for p in (root/directory).rglob('*')
                         if p.is_file() and '__pycache__' not in p.parts)
        names.add('docs/provenance.json')
        recipes={name:product.sha(root/name) for name in names}
        for profile,component in [('omarchy','opaque-consumer'),('cachyos-plasma','kwin-opaque')]:
            receipt=dict(profile=profile,recipe_files=recipes,
                         runtime_files={component+'/fixture': '0'*64})
            report=product.write_component_map(root,receipt,self.notices)
            self.assertFalse(report['release_ready'])
            self.assertEqual(len(report['component_runtime_files']),1)
            self.assertIn('docs/licensing/modules.json',report['policy_files'])
            self.assertTrue(all(o['inventoried_sources'] for o in report['outputs']))
