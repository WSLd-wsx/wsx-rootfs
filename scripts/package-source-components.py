#!/usr/bin/env python3
"""Package the validated source assembly as a paired, relocatable runtime."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import shutil
from component_materials import verify, source_files, source_descriptor


def package(work, output):
    work = work.resolve(strict=True)
    receipt = json.loads((work / 'component-source.json').read_text())
    if receipt.get('compiled') is not True or receipt.get('runtime_assembled') is not True:
        raise ValueError('Completed source assembly required')
    actual = {}
    for path in sorted((work / 'private').rglob('*')):
        if path.is_symlink():
            raise ValueError('Assembly must materialize component links')
        if path.is_file() and path != work / 'private/manifest.json':
            with path.open('rb') as stream:
                actual[str(path.relative_to(work / 'private'))] = hashlib.file_digest(stream, 'sha256').hexdigest()
    if not actual or actual != receipt['runtime_files']:
        raise ValueError('Runtime changed after assembly')
    materials = verify(work)
    output.mkdir(parents=True, exist_ok=False)
    profile = receipt.get('profile', 'omarchy')
    if profile not in ('omarchy', 'cachyos-plasma'):
        raise ValueError('Unknown component profile')
    archive = output / f'wsx-{profile}-components-x86_64.tar.zst'
    subprocess.run(['tar', '--zstd', '-cf', str(archive.resolve()), '-C', str(work),
                    'private', 'component-source.json', 'component-materials/notices', 'component-materials/materials.json'], check=True)
    material_files=source_files(materials)
    for name, relative in material_files.items():
        shutil.copy2(work/'component-materials'/relative, output/name)
    shutil.copy2(work/'component-materials/materials.json', output/'materials.json')
    with archive.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    manifest = dict(schema_version=materials['schema_version'], profile=profile, architecture='x86_64',
                    origin='source-build', archive=archive.name, sha256=digest,
                    size=archive.stat().st_size, hardware_validation='not_run',
                    components=(['mesa', 'venus', 'kwin'] if profile == 'cachyos-plasma' else ['mesa', 'venus', 'aquamarine', 'hyprland']),
                    source_receipt=receipt, source_materials=source_descriptor(materials),
                    materials_sha256=hashlib.sha256((output/'materials.json').read_bytes()).hexdigest(),
                    distribution_allowed=False, license_review='pending', corresponding_source_complete=False)
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    sums = []
    for path in (archive, *(output/n for n in material_files), output/'materials.json', output/'manifest.json'):
        with path.open('rb') as stream:
            sums.append(f'{hashlib.file_digest(stream, "sha256").hexdigest()}  {path.name}\n')
    (output/'SHA256SUMS').write_text(''.join(sums))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('work', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    package(args.work, args.output)
