import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from contract import identity, parse_install, resolve, validate


def manifest(version='4.0.6-r1', distro='wsx-omarchy'):
    return dict(schema_version=1, distribution_id=distro, image_version=version,
                upstream_release='v' + version.split('-r')[0], upstream_commit='a'*40,
                wsx_revision=int(version.split('-r')[1]), architecture='x86_64',
                archive_format='tar.zst', asset_name=f'{distro}-{version}-x86_64.rootfs.tar.zst',
                sha256='b'*64, build_identity='c'*64, build_commit='d'*40,
                compressed_size=100, unpacked_size=200, installation_space_required=400,
                guest_interface_abi=1, minimum_wsx_core_version='1.0.0',
                graphics_components=[dict(name='fixture', version='1', inputs_sha256='e'*64)],
                kernel_requirements={'fixture': True},
                validation=dict(build='passed', offline='passed', wsl_boot='passed',
                                gpu_first_frame='passed', desktop='passed', stability='not_run'))


def release(m=None, **changes):
    m = m or manifest()
    return dict(draft=False, prerelease=False, assets_verified=True, manifest=m,
                tag_name=m['distribution_id']+'-'+m['image_version']) | changes


class ContractTests(unittest.TestCase):
    def test_hyphenated_distro(self):
        self.assertEqual(parse_install('wsx-cachyos-plasma-4.0.6-r1'), ('wsx-cachyos-plasma', '4.0.6-r1'))
        with self.assertRaises(ValueError):
            parse_install('wsx-unknown-4.0.6-r1')

    def test_revision_order_and_distro_isolation(self):
        rows = [release(manifest('4.0.6-r2')), release(manifest('4.0.6-r10')),
                release(manifest('99.0.0-r1', 'wsx-cachyos-plasma'))]
        self.assertEqual(resolve('wsx-omarchy', rows, lambda m: True)['wsx_revision'], 10)

    def test_draft_prerelease_partial_never_install(self):
        for flags in ({'draft': True}, {'prerelease': True}, {'assets_verified': False}):
            with self.subTest(flags=flags), self.assertRaises(ValueError):
                resolve('wsx-omarchy-4.0.6-r1', [release(**flags)], lambda m: True)

    def test_explicit_version_never_falls_back(self):
        with self.assertRaises(ValueError):
            resolve('wsx-omarchy-4.0.6-r2', [release()], lambda m: True)

    def test_unknown_compatibility_and_failed_hardware_reject(self):
        for key in ('guest_interface_abi', 'minimum_wsx_core_version'):
            m = manifest(); m[key] = None
            validate(m)
            with self.assertRaises(ValueError):
                resolve('wsx-omarchy', [release(m)], lambda m: True)
        m = manifest(); m['validation']['gpu_first_frame'] = 'not_run'
        with self.assertRaises(ValueError):
            resolve('wsx-omarchy', [release(m)], lambda m: True)

    def test_corrupt_manifest_rejects(self):
        for key, value in [('schema_version', True), ('wsx_revision', True), ('wsx_revision', 2), ('asset_name', '../escape'), ('sha256', 'bad'),
                           ('compressed_size', True), ('build_commit', 'main')]:
            m = manifest(); m[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate(m)

    def test_cachyos_requires_explicit_supported_cpu_contract(self):
        m = manifest('2026.11.1-r1', 'wsx-cachyos-plasma')
        with self.assertRaisesRegex(ValueError, 'CPU requirements'):
            validate(m)
        m['cpu_requirements'] = {'architecture_level': 'x86-64-v3'}
        validate(m)
        m['cpu_requirements'] = {'architecture_level': 'unknown'}
        with self.assertRaisesRegex(ValueError, 'CPU requirements'):
            validate(m)

    def test_identity_canonical_and_input_sensitive(self):
        self.assertEqual(identity({'a':1,'b':2}), identity({'b':2,'a':1}))
        self.assertNotEqual(identity({'a':1}), identity({'a':2}))


if __name__ == '__main__':
    unittest.main()
