#!/usr/bin/env python3
"""Assemble fresh source outputs without borrowing historical acceptance evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
COMPONENTS = ('mesa', 'venus', 'aquamarine', 'hyprland')


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def files(directory):
    return {str(p.relative_to(directory)): sha(p) for p in sorted(directory.rglob('*'))
            if p.is_file() and p != directory/'manifest.json'}


def validate_prefix(prefix):
    if prefix.is_symlink() or not prefix.is_dir():
        raise ValueError('Missing or redirected component prefix: ' + str(prefix))
    for path in prefix.rglob('*'):
        resolved = path.resolve(strict=True)
        if not resolved.is_relative_to(prefix.resolve()):
            raise ValueError('Component link escapes its prefix: ' + str(path))
        if path.is_symlink() and resolved.is_dir():
            raise ValueError('Directory links require explicit assembly review')
        if not path.is_file() and not path.is_dir():
            raise ValueError('Unsupported component file: ' + str(path))


def merge_prefix(prefix, target):
    validate_prefix(prefix)
    target.mkdir(parents=True, exist_ok=True)
    for path in sorted(prefix.rglob('*')):
        relative = path.relative_to(prefix)
        if relative == Path('manifest.json'):
            continue
        dest = target/relative
        if path.is_dir():
            dest.mkdir(parents=True, exist_ok=True)
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                if not dest.is_file() or sha(dest) != sha(path):
                    raise ValueError('Conflicting component output: ' + str(relative))
            else:
                # Materialize only links already verified to stay inside the prefix.
                shutil.copy2(path, dest)
            dest.chmod(0o755 if path.stat().st_mode & 0o111 else 0o644)


def assemble(build, work):
    receipt = json.loads((build/'source-build.json').read_text())
    if receipt.get('origin') != 'source-build' or receipt.get('compiled') is not True:
        raise ValueError('Fresh completed source build receipt required')
    pins = json.loads((ROOT/'components/sources.json').read_text())
    if receipt['archives'] != {n:dict(url=p['url'], sha256=p['sha256']) for n,p in pins.items() if n != 'schema_version'}:
        raise ValueError('Source receipt differs from current source pins')
    required_inputs = {'components/sources.json', 'components/builder.json',
                       'scripts/build-components.py', 'scripts/assemble-source-components.py'}
    if not required_inputs.issubset(receipt.get('recipe_files', {})):
        raise ValueError('Incomplete source recipe receipt')
    for name, expected in receipt['recipe_files'].items():
        path = ROOT/name
        if not path.resolve().is_relative_to(ROOT) or sha(path) != expected:
            raise ValueError('Recipe input changed after compilation: ' + name)
    profile = receipt.get('profile', 'omarchy')
    if profile not in ('omarchy', 'cachyos-plasma'):
        raise ValueError('Unknown component profile')
    components = ('mesa', 'venus', 'kwin') if profile == 'cachyos-plasma' else COMPONENTS
    reports = {}
    for name in components:
        folder = build/name
        report = json.loads((folder/'result.json').read_text())
        if report.get('passed') is not True and report.get('pass') is not True:
            raise ValueError('Missing successful source component: ' + name)
        validate_prefix(folder/'prefix')
        actual = {str(p.relative_to(folder/'prefix')): sha(p)
                  for p in sorted((folder/'prefix').rglob('*')) if p.is_file()}
        if not actual or actual != receipt.get('output_files', {}).get(name):
            raise ValueError('Compiled output changed: ' + name)
        if name in ('aquamarine', 'hyprland') and (report.get('revision') != pins[name]['commit']
                or report.get('archive_sha256') != pins[name]['sha256']):
            raise ValueError('Compositor source receipt mismatch: ' + name)
        if name == 'kwin' and (report.get('version') != pins['kwin']['version'] or report.get('source_sha256') != pins['kwin']['sha256']):
            raise ValueError('KWin source receipt mismatch')
        reports[name] = report
    for name in ('mesa', 'venus'):
        prefix = build/name/'prefix'
        manifest = json.loads((prefix/'manifest.json').read_text())
        if manifest.get('source_sha256') != pins[name]['sha256']:
            raise ValueError('Source manifest mismatch: ' + name)
        required_flags = ('linear_shared_compat', 'opaque_gbm_export', 'opaque_consumer') if name == 'mesa' else ('zink_drm_identity', 'opaque_wsi', 'opaque_import')
        if any(manifest.get(flag) is not True for flag in required_flags):
            raise ValueError('Missing paired source capability: ' + name)
        if name == 'mesa' and manifest.get('presentation_staging_policy') is not False:
            raise ValueError('Unexpected staging policy')
        if name == 'venus' and manifest.get('direct_wsi') != 'linear-v1':
            raise ValueError('Missing paired direct WSI')
        if not manifest.get('files') or manifest['files'] != files(prefix):
            raise ValueError('Output manifest mismatch: ' + name)
    destination = work/'private'
    destination.mkdir(exist_ok=False)
    for name in ('mesa','venus'):
        merge_prefix(build/name/'prefix', destination/name)
        shutil.copy2(build/name/'prefix/manifest.json', destination/name/'manifest.json')
    if profile == 'cachyos-plasma':
        consumer = destination/'kwin-opaque'
        merge_prefix(build/'kwin/prefix', consumer)
        required = ('bin/kwin_wayland', 'lib/libkwin.so.6')
        if not all((consumer/p).is_file() for p in required):
            raise ValueError('Incomplete private KWin runtime')
        (consumer/'manifest.json').write_text(json.dumps(dict(abi=2, origin='source-build',
            hardware_validation='not_run', version=pins['kwin']['version'],
            files=files(consumer)), indent=2)+'\n')
    else:
        consumer = destination/'opaque-consumer'
        for name in ('aquamarine', 'hyprland'):
            merge_prefix(build/name/'prefix', consumer)
        required = ('bin/Hyprland','bin/hyprctl','lib/libaquamarine.so.14')
        if not all((consumer/p).is_file() for p in required):
            raise ValueError('Incomplete source-built compositor runtime')
        # ABI 2 is the declared paired consumer contract, not hardware acceptance.
        (consumer/'manifest.json').write_text(json.dumps(dict(
            abi=2, origin='source-build', hardware_validation='not_run',
            inputs={n:pins[n] for n in ('aquamarine','hyprland','udis86','glaze')},
            files=files(consumer)), indent=2)+'\n')
    for path in destination.rglob('*'):
        if path.is_dir():
            path.chmod(0o755)
        elif path.is_file():
            with path.open('rb') as stream:
                elf = stream.read(4) == b'\x7fELF'
            if elf:
                dynamic = subprocess.check_output(['readelf', '-d', str(path)], text=True)
                if '(RPATH)' in dynamic or '(RUNPATH)' in dynamic:
                    raise ValueError('Private ELF retains a search path requiring review: ' + str(path))
    result = dict(receipt, runtime_assembled=True, component_reports=reports,
                  source_build_receipt_sha256=sha(build/'source-build.json'),
                  runtime_files=files(destination))
    (work/'component-source.json').write_text(json.dumps(result, indent=2)+'\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('build', type=Path)
    parser.add_argument('work', type=Path)
    args = parser.parse_args()
    assemble(args.build.resolve(strict=True), args.work.resolve(strict=True))


if __name__ == '__main__':
    main()
