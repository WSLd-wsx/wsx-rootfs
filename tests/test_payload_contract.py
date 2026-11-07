"""Historical and source-paired payloads have distinct, closed asset sets."""
import copy
import unittest
from payload_contract import asset_names, validate_completion, SOURCE_ASSETS
from test_contract import manifest


class PayloadContract(unittest.TestCase):
    def marker(self, m):
        result = dict(schema_version=1, build_identity=m['build_identity'],
                      assets={n: dict(size=1, sha256='0'*64) for n in asset_names(m)})
        result['assets'][m['asset_name']] = dict(size=m['compressed_size'], sha256=m['sha256'])
        return result

    def test_both_distributions_support_old_and_paired_formats(self):
        for distro in ('wsx-omarchy', 'wsx-cachyos-plasma'):
            for paired in (False, True):
                m = manifest(); m['distribution_id'] = distro
                if paired: m['source_delivery_schema'] = 1
                self.assertEqual(len(asset_names(m)), 8 if paired else 5)
                validate_completion(m, self.marker(m))

    def test_unknown_or_boolean_schema_rejected(self):
        for value in (0, 3, True, '1', None):
            m = manifest(); m['source_delivery_schema'] = value
            with self.subTest(value=value), self.assertRaises(ValueError): asset_names(m)

    def test_missing_extra_or_wrong_identity_marker_rejected(self):
        m = manifest(); m['source_delivery_schema'] = 1
        for mutation in ('missing', 'extra', 'identity'):
            marker = self.marker(m)
            if mutation == 'missing': del marker['assets'][SOURCE_ASSETS[0]]
            if mutation == 'extra': marker['assets']['surprise'] = dict(size=1, sha256='0'*64)
            if mutation == 'identity': marker['build_identity'] = 'f'*64
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): validate_completion(m, marker)
