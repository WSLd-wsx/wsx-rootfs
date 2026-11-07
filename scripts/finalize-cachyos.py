#!/usr/bin/env python3
"""Archive an offline-validated CachyOS snapshot and prepare Draft assets."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
from archive import pack
from archive_policy import fingerprint
from source_delivery import attach_current as attach
from payload_contract import asset_names
from product_licenses import verify_image_map
from desktop_contract import declaration, runtime_pin
from image_materials import verify_image_snapshot
from contract import validate
import jsonschema

ROOT = Path(__file__).resolve().parents[1]

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('work', type=Path)
p.add_argument('--desktop-runtime-receipt', type=Path)
p.add_argument('--minimum-core-version')
a = p.parse_args()
work = a.work.resolve(strict=True)
build = json.loads((work/'build.json').read_text())
validation = json.loads((work/'validation.json').read_text())
if validation['offline'] != 'passed':
    raise ValueError('Offline checks did not pass')
package = json.loads((work/'component-source.json').read_text())
if package.get('profile') != 'cachyos-plasma' or package.get('compiled') is not True or package.get('runtime_assembled') is not True:
    raise ValueError('Completed paired CachyOS source build required')
for relative, expected in package['runtime_files'].items():
    path = (work/'private'/relative).resolve(strict=True)
    if not path.is_relative_to((work/'private').resolve()) or sha(path) != expected:
        raise ValueError('Component changed after admission: ' + relative)
component_identity = hashlib.sha256(json.dumps(package, sort_keys=True).encode()).hexdigest()
verify_image_snapshot(ROOT, work)
verify_image_map(work/'rootfs', work/'image-materials')
desktop = declaration(work/'rootfs', a.desktop_runtime_receipt, a.minimum_core_version)
payload = work/'payload'
payload.mkdir(exist_ok=False)
name = build['tag']+'-x86_64.rootfs.tar.zst'
policy_path = work/'archive-policy.json'
policy = json.loads(policy_path.read_text()) if policy_path.is_file() else {'mode': 'full', 'recipe_fingerprint': fingerprint(build)}
if policy.get('recipe_fingerprint') != fingerprint(build):
    raise ValueError('Archive policy fingerprint differs from current recipe')
compression = pack(work/'rootfs', payload/name, policy=policy)
(work/'compression.json').write_text(json.dumps(compression, indent=2)+'\n')
if compression['compressed_size'] >= 2**31:
    raise ValueError('Archive exceeds GitHub asset limit')
sources = dict(build_inputs=build, installer=json.loads((ROOT/'distros/cachyos-plasma/upstream/source.json').read_text()),
    snapshot_kind='explicit WSX build date, not an official CachyOS release',
    arch_repository_snapshot='https://archive.archlinux.org/repos/2026/10/28/',
    rolling_mirrors_restored_after_build=True, component_package=package,
    plasma_compatibility=json.loads((work/'rootfs/usr/lib/wsx/plasma-compat.json').read_text()),
    component_manifests={n:json.loads((work/'private'/n/'manifest.json').read_text()) for n in ('mesa', 'venus', 'kwin-opaque')},
    inspected_kwin_patch_inputs=json.loads((ROOT/'components/cachyos-provenance.json').read_text()),
    builder=json.loads((ROOT/'components/builder.json').read_text()),
    build_packages=(work/'build-packages.txt').read_text().splitlines(),
    rootfs_packages=(work/'rootfs-packages.txt').read_text().splitlines(),
    build_repositories=(work/'build-repositories.conf').read_text(),
    rootfs_repositories=(work/'rootfs-repositories.conf').read_text(),
    repository_package_versions=(work/'repository-packages.txt').read_text().splitlines(),
    offline_checks=json.loads((work/'offline-details.json').read_text()), compression=compression,
    component_reuse=json.loads((work/'component-reuse.json').read_text()),
    component_build_packages=(work/'components/build-packages.txt').read_text().splitlines(),
    component_build_repositories=(work/'components/build-repositories.conf').read_text(), byte_reproducible=False)
sources['component_source_delivery'] = attach(work, payload)
(payload/'sources.json').write_text(json.dumps(sources, indent=2)+'\n')
inputs = build['inputs']
graphics = [dict(name=n, version=v, inputs_sha256=component_identity) for n,v in
            [('mesa','26.1.8'), ('venus','26.2.4'), ('kwin','6.8.1')]]
m = dict(schema_version=1, source_delivery_schema=sources['component_source_delivery']['schema_version'], distribution_id='wsx-cachyos-plasma', image_version=inputs['snapshot']+'-r'+str(inputs['wsx_revision']),
    upstream_release=inputs['snapshot'], upstream_commit=inputs['installer_commit'], wsx_revision=inputs['wsx_revision'],
    architecture='x86_64', archive_format='tar.zst', asset_name=name, sha256=sha(payload/name),
    compressed_size=compression['compressed_size'], unpacked_size=compression['logical_size'],
    installation_space_required=compression['logical_size']*3+compression['compressed_size']+1024**3,
    build_commit=build['build_commit'], build_identity=build['build_identity'], guest_interface_abi=1,
    minimum_wsx_core_version=None, graphics_components=graphics,
    cpu_requirements={'architecture_level':'x86-64-v3'},
    kernel_requirements={'selection_owner':'wsx-core', 'exact_kernel_release_and_symbol_crcs_required':True,
        'opaque_producer_abi':1, 'opaque_consumer_abi':2, 'drm_embedded_bases_at_allocation_start':True,
        'rejected_module_sha256':['70d83be693bc714378b41f22ff38f2a1d459b363b853be214114c5988600def0']},
    validation=validation)
if bool(a.desktop_runtime_receipt) != bool(a.minimum_core_version):
    raise ValueError('Desktop pairing and minimum Core must be supplied together')
m['desktop_compatibility'] = desktop
m['minimum_wsx_core_version'] = runtime_pin()[0]['minimum_wsx_core_version']
validate(m)
jsonschema.validate(m, json.loads((ROOT/'schema/manifest-v1.schema.json').read_text()))
(payload/'manifest.json').write_text(json.dumps(m, indent=2)+'\n')
shutil.copy2(work/'validation.json', payload/'validation.json')
names = [n for n in asset_names(m) if n != 'SHA256SUMS']
(payload/'SHA256SUMS').write_text(''.join(f'{sha(payload/n)}  {n}\n' for n in names))
print(json.dumps({'asset':name, 'sha256':m['sha256']}))
