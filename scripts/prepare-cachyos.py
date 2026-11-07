#!/usr/bin/env python3
"""Identify one explicit CachyOS snapshot candidate and check completed Drafts."""
import argparse
from datetime import date
import json
from pathlib import Path
import re
import subprocess
import tempfile
from contract import identity, validate
from operations_provenance import attach as attach_operations
from payload_contract import validate_completion
from source_support import require_source_recipe
from release_access import api, download, releases, verify_remote

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--snapshot', required=True, help='Explicit internal WSX snapshot date YYYY.M.D')
p.add_argument('--revision', type=int, required=True)
p.add_argument('--repo', required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
if not re.fullmatch(r'[0-9]{4}\.(?:[1-9]|1[0-2])\.(?:[1-9]|[12][0-9]|3[01])', a.snapshot):
    raise ValueError('Snapshot must be an explicit date YYYY.M.D without zero padding')
date(*map(int, a.snapshot.split('.')))
if a.revision < 1:
    raise ValueError('Revision must be positive')
require_source_recipe('wsx-cachyos-plasma')
lock = json.loads((ROOT/'distros/cachyos-plasma/upstream/source.json').read_text())
names = subprocess.check_output(['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard', 'scripts', 'distros/cachyos-plasma',
    'LICENSE', 'LICENSE-MAP.md', 'components', 'vendor', 'schema', 'guest', 'docs/licensing/OUTPUT-LICENSES.md','docs/licensing/PRIVATE-ARTIFACTS.md','docs/licensing/modules.json', 'docs/licensing/rules.json', 'docs/licensing/license-text-sources.json', 'docs/licensing/licenses'], cwd=ROOT).decode().split('\0')
hashes = {name: identity({'bytes': (ROOT/name).read_bytes().hex()}) for name in sorted(set(names)) if name and (ROOT/name).is_file()}
inputs = dict(distribution_id='wsx-cachyos-plasma', architecture='x86_64',
              wsx_revision=a.revision, snapshot=a.snapshot, installer_commit=lock['commit'],
              snapshot_kind='explicit-wsx-build-date-not-upstream-release', recipe_files=hashes)
inputs = attach_operations(inputs)
build_id = identity(inputs)
tag = 'wsx-cachyos-plasma-'+a.snapshot+'-r'+str(a.revision)
completed = False
for release in releases(a.repo):
    if release['tag_name'] != tag:
        continue
    if release['prerelease']:
        raise ValueError('Existing version is a prerelease')
    assets = api(f'repos/{a.repo}/releases/{release["id"]}/assets?per_page=100')
    documents = {}
    with tempfile.TemporaryDirectory() as temp:
        for asset in assets:
            if asset['name'] in ('manifest.json', 'completion.json'):
                path = Path(temp)/asset['name']
                download(a.repo, asset, path)
                item = json.loads(path.read_text())
                if item.get('build_identity') != build_id:
                    raise ValueError('Version slot has different inputs; select a new revision')
                documents[asset['name']] = item
        if 'completion.json' in documents:
            manifest = validate(documents['manifest.json'])
            marker = documents['completion.json']
            if manifest['distribution_id'] != 'wsx-cachyos-plasma' or tag != manifest['distribution_id']+'-'+manifest['image_version']:
                raise ValueError('Release identity mismatch')
            validate_completion(manifest, marker)
            verify_remote(a.repo, release, marker)
            completed = True
    if not release['draft'] and not completed:
        raise ValueError('Public version is incomplete and immutable')
output = dict(inputs=inputs, build_identity=build_id, tag=tag, completed=completed,
              build_commit=subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip())
a.output.parent.mkdir(parents=True, exist_ok=True)
a.output.write_text(json.dumps(output, indent=2)+'\n')
print(json.dumps({'tag':tag, 'build_identity':build_id, 'completed':completed}))
