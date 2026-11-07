#!/usr/bin/env python3
"""Resolve inputs and detect a complete immutable candidate before building."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import tempfile
from contract import identity, validate
from operations_provenance import attach as attach_operations
from payload_contract import validate_completion
from release_access import releases, api, download, verify_remote

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--version')
    p.add_argument('--revision', type=int, default=0)
    p.add_argument('--repo', required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    if args.revision < 0:
        raise ValueError('Revision must be nonnegative; zero selects the recipe mapping')
    argv = ['python3', str(ROOT/'scripts/releases.py')]
    if args.version:
        argv += ['--version', args.version]
    upstream = json.loads(subprocess.check_output(argv, text=True))
    if args.revision == 0:
        mapping = json.loads((ROOT/'distros/omarchy/revisions.json').read_text())
        args.revision = mapping['upstream'].get(upstream['upstream_release'].removeprefix('v'), mapping['default'])
        if type(args.revision) is not int or args.revision < 1:
            raise ValueError('Invalid recipe revision mapping')
    # Hash tracked and non-ignored recipe inputs, including operational license metadata.
    names = subprocess.check_output(['git','ls-files','-z','--cached','--others','--exclude-standard','scripts','distros/omarchy',
              'LICENSE','LICENSE-MAP.md','components','vendor','schema','guest','docs/licensing/OUTPUT-LICENSES.md','docs/licensing/PRIVATE-ARTIFACTS.md','docs/licensing/modules.json','docs/licensing/rules.json','docs/licensing/license-text-sources.json','docs/licensing/licenses'], cwd=ROOT).decode().split('\0')
    hashes = {name: identity({'bytes': (ROOT/name).read_bytes().hex()}) for name in sorted(set(names)) if name and (ROOT/name).is_file() and name != 'distros/omarchy/revisions.json'}
    inputs = dict(distribution_id='wsx-omarchy', architecture='x86_64', wsx_revision=args.revision,
                  upstream_release=upstream['upstream_release'], upstream_commit=upstream['upstream_commit'],
                  recipe_files=hashes)
    inputs = attach_operations(inputs)
    build_id = identity(inputs)
    tag = 'wsx-omarchy-' + upstream['upstream_release'].removeprefix('v') + '-r' + str(args.revision)
    completed = False
    for release in releases(args.repo):
        if release['tag_name'] != tag:
            continue
        assets = api(f'repos/{args.repo}/releases/{release["id"]}/assets?per_page=100')
        if release['prerelease']:
            raise ValueError('Existing version is a prerelease')
        documents = {}
        with tempfile.TemporaryDirectory() as temporary:
            for asset in assets:
                if asset['name'] not in ('manifest.json','completion.json'):
                    continue
                path = Path(temporary)/asset['name']; download(args.repo, asset, path)
                data = json.loads(path.read_text())
                if data.get('build_identity') != build_id:
                    raise ValueError('Version slot has different inputs; select a new revision')
                documents[asset['name']] = data
            if 'completion.json' in documents:
                if 'manifest.json' not in documents:
                    raise ValueError('Completion marker lacks a manifest')
                manifest = validate(documents['manifest.json'])
                if manifest['distribution_id'] != inputs['distribution_id'] or tag != manifest['distribution_id']+'-'+manifest['image_version']:
                    raise ValueError('Release tag and manifest identity mismatch')
                marker = documents['completion.json']
                validate_completion(manifest, marker)
                verify_remote(args.repo, release, marker)
                completed = True
        if not release['draft'] and not completed:
            raise ValueError('Public version is incomplete and immutable')
    output = dict(inputs=inputs, build_identity=build_id, tag=tag, completed=completed,
                  upstream=upstream, build_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps({'tag':tag,'build_identity':build_id,'completed':completed}))


if __name__ == '__main__':
    main()
