"""Prevent a module label from silently replacing existing third-party terms."""
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('license_modules', ROOT/'scripts/audit-license-modules.py')
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)


class Modules(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((ROOT/'docs/licensing/modules.json').read_text())

    def entry(self, path, rule, group):
        return dict(path=path, rule=rule, group=group, sha256='0'*64)

    def test_kwin_mit_notice_survives_combination_membership(self):
        result = module.classify(self.entry('vendor/wsx-proto/guest-opaque/kwin-framebuffer.c',
            'existing-mit', 'retain-original'), self.config)
        self.assertEqual(result['module'], 'kwin-combination')
        self.assertEqual(result['existing_rule'], 'existing-mit')
        self.assertFalse(result['license_grant'])

    def test_existing_terms_cannot_be_mapped_to_polyform(self):
        self.config['rule_modules']['existing-mit'] = 'wsx-independent'
        with self.assertRaisesRegex(ValueError, 'cannot default'):
            module.classify(self.entry('vendor/wsx-proto/input/guest.c',
                'existing-mit', 'retain-original'), self.config)

    def test_compilation_recipe_excluded_from_polyform_default(self):
        result = module.classify(self.entry('scripts/build-kwin.py',
            'new-component-producer-origin-review', 'conditional-future-license'), self.config)
        self.assertEqual(result['module'], 'gpl-build-materials')

    def test_unknown_rule_fails(self):
        with self.assertRaisesRegex(ValueError, 'Missing module'):
            module.classify(self.entry('new', 'unknown', 'conditional-future-license'), self.config)

    def test_selected_original_has_no_addendum(self):
        module.validate_selection(self.config)

    def test_additional_trial_permission_rejected(self):
        self.config['license_selection']['additional_permissions'] = ['30-day trial']
        with self.assertRaisesRegex(ValueError, 'without additions'):
            module.validate_selection(self.config)

    def test_source_only_restriction_rejected(self):
        self.config['license_selection']['additional_restrictions'] = ['source-only']
        with self.assertRaisesRegex(ValueError, 'without additions'):
            module.validate_selection(self.config)

    def test_unreviewed_activation_rejected(self):
        self.config.pop('activation')
        with self.assertRaisesRegex(ValueError, 'owner-approved'):
            module.validate_selection(self.config)
