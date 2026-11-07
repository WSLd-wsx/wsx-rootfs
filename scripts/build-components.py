#!/usr/bin/env python3
"""Adapt inspected WSX builders in a disposable copy; never use local artifacts."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import time
from build_resources import resources
from license_inputs import paths as license_paths
from product_licenses import check_boundaries

ROOT = Path(__file__).resolve().parents[1]
COMMANDS = []

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def run(*args):
    command = list(map(str, args))
    COMMANDS.append(command)
    started = time.monotonic()
    print('Starting component builder: ' + ' '.join(command), flush=True)
    try:
        subprocess.run(command, check=True)
    finally:
        print(f'Component builder elapsed: {time.monotonic() - started:.1f}s ({command[1]})', flush=True)


def build(args):
    capacity = resources()
    jobs = str(capacity['jobs'])
    print('Compiler resources: ' + json.dumps(capacity), flush=True)
    out = args.output.resolve()
    sources = out/'builders'
    shutil.copytree(ROOT/'vendor/wsx-proto', sources)
    builder = sources/'guest-compat/build.py'
    text = builder.read_text()
    old = "pin = json.loads((ROOT / 'prototypes/venus-rutabaga/sources.lock.json').read_text())['archives']['mesa']"
    pin = json.loads((ROOT/'components/sources.json').read_text())['mesa']
    pin.update(directory='mesa-'+pin['version'])
    if text.count(old) != 1:
        raise ValueError('Unexpected vendored builder structure')
    text = text.replace(old, 'pin = ' + repr(pin))
    old = "archive = ROOT / 'artifacts/venus-rutabaga/inputs-01' / pin['file']"
    if text.count(old) != 1:
        raise ValueError('Unexpected archive binding')
    text = text.replace(old, 'archive = Path(' + repr(str(args.archives.resolve()/'mesa.archive')) + ')')
    old = "'-j', '3'"
    if text.count(old) != 1:
        raise ValueError('Unexpected Mesa concurrency binding')
    builder.write_text(text.replace(old, "'-j', " + repr(jobs)))
    run(sys.executable, builder, out/'mesa', '--import-diagnostics', '--negotiated-export',
        '--modifier-features2', '--linear-feedback-compat', '--linear-shared-compat',
        '--linear-modifier-feedback', '--linear-depth-segregation', '--opaque-gbm-export', '--opaque-consumer')
    run(sys.executable, sources/'guest-compat/build-venus.py', out/'venus',
        '--archive', args.archives/'venus.archive', '--nv-linear-color', '--opaque-import',
        '--direct-wsi', '--opaque-wsi', '--jobs', jobs)
    if getattr(args, 'profile', 'omarchy') == 'cachyos-plasma':
        run(sys.executable, ROOT/'scripts/build-kwin.py', args.archives/'kwin.archive', out/'kwin', '--jobs', jobs)
        return
    compositor = sources/'guest-opaque/build-compositor.py'
    initial = compositor.read_text()
    marker = "'-DCMAKE_BUILD_TYPE=Release','-DBUILD_TESTING=OFF',"
    if initial.count(marker) != 1:
        raise ValueError('Unexpected compositor install configuration')
    compositor.write_text(initial.replace(marker, marker + "'-DCMAKE_SKIP_RPATH=ON',"))
    run(sys.executable, sources/'guest-opaque/build-compositor.py', 'aquamarine', out/'aquamarine',
        '--archive', args.archives/'aquamarine.archive', '--jobs', jobs)
    with tarfile.open(args.archives/'glaze.archive') as archive:
        archive.extractall(out/'glaze', filter='data')
    glaze_source = next((out/'glaze').iterdir())
    compositor_builder = sources/'guest-opaque/build-compositor.py'
    text = compositor_builder.read_text()
    old = "configure += ['-DNO_HYPRPM=ON',"
    if text.count(old) != 1:
        raise ValueError('Unexpected compositor configure structure')
    flags = ['-DFETCHCONTENT_SOURCE_DIR_GLAZE='+str(glaze_source),
             '-DCMAKE_DISABLE_FIND_PACKAGE_glaze=ON', '-DFETCHCONTENT_FULLY_DISCONNECTED=ON',
             '-DNO_HYPRPM=ON']
    text = text.replace(old, 'configure += [' + ','.join(map(repr, flags)) + ',')
    compositor_builder.write_text(text)
    run(sys.executable, sources/'guest-opaque/build-compositor.py', 'hyprland', out/'hyprland',
        '--archive', args.archives/'hyprland.archive', '--udis86-archive', args.archives/'udis86.archive',
        '--build-deps-prefix', out/'aquamarine/prefix', '--jobs', jobs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archives', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--profile', choices=('omarchy', 'cachyos-plasma'), default='omarchy')
    args = parser.parse_args()
    pins = json.loads((ROOT/'components/sources.json').read_text())
    # Validate every archive even when invoked without the download helper.
    archives = {}
    for name, pin in pins.items():
        if name == 'schema_version':
            continue
        archive = args.archives/(name+'.archive')
        if sha(archive) != pin['sha256']:
            raise ValueError('Source archive hash mismatch: ' + name)
        archives[name] = dict(url=pin['url'], sha256=pin['sha256'])
    args.output.mkdir(parents=True, exist_ok=False)
    check_boundaries(ROOT)
    inputs = {name: sha(ROOT/name) for name in license_paths(ROOT)}
    for directory in ('vendor', 'scripts', 'components', 'distros', 'guest', 'schema', '.github/workflows', 'docs/licensing/licenses'):
        for path in sorted((ROOT/directory).rglob('*')):
            if path.is_file() and '__pycache__' not in path.parts:
                inputs[str(path.relative_to(ROOT))] = sha(path)
    for name in ('docs/provenance.json', 'docs/licensing/rules.json', 'docs/licensing/license-text-sources.json'):
        if (ROOT/name).is_file():
            inputs[name] = sha(ROOT/name)
    receipt = dict(schema_version=1, origin='source-build', compiled=False,
                   runtime_assembled=False, profile=args.profile, hardware_validation='not_run',
                   license_review='pending', corresponding_source_complete=False,
                   archives=archives, recipe_files=inputs, commands=COMMANDS)
    COMMANDS.clear()
    try:
        build(args)
        receipt['output_files'] = {
            name: {str(path.relative_to(args.output/name/'prefix')): sha(path)
                   for path in sorted((args.output/name/'prefix').rglob('*')) if path.is_file()}
            for name in (('mesa', 'venus', 'kwin') if args.profile == 'cachyos-plasma' else ('mesa', 'venus', 'aquamarine', 'hyprland'))
        }
        receipt['compiled'] = True
    except Exception as error:
        receipt['error'] = str(error)
        raise
    finally:
        receipt['adapted_builders'] = {
            str(path.relative_to(args.output)): sha(path)
            for path in sorted((args.output/'builders').rglob('*')) if path.is_file()
        }
        (args.output/'source-build.json').write_text(json.dumps(receipt, indent=2)+'\n')


if __name__ == '__main__':
    main()
