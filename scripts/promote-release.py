#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Verify a public rootfs prerelease before optional stable promotion."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from contract import parse_install, validate
from payload_contract import asset_names, source_asset_names, validate_completion
from source_delivery import required_assets, check_public_source_delivery

REPO = 'WSLd-wsx/wsx-rootfs'

def api(path):
    return json.loads(subprocess.check_output(['gh','api',path],text=True))

def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()

def release_snapshot(tag):
    _, version = parse_install(tag)
    if not version:
        raise ValueError('An exact versioned tag is required')
    repo = api('repos/'+REPO)
    if repo.get('full_name') != REPO or repo.get('private') is not False:
        raise ValueError('Stable promotion requires the approved public repository')
    release = api(f'repos/{REPO}/releases/tags/{tag}')
    if release.get('tag_name') != tag or release.get('draft') is not False or release.get('prerelease') is not True:
        raise ValueError('Expected the exact published prerelease')
    assets = api(f'repos/{REPO}/releases/{release["id"]}/assets?per_page=100')
    names = [a.get('name') for a in assets]
    if any(not isinstance(name, str) or not name or name in ('.', '..')
           or '/' in name or '\\' in name for name in names) or len(names) != len(set(names)):
        raise ValueError('Unsafe or duplicate release assets')
    fields = ('id', 'name', 'size', 'digest', 'state')
    rows = sorted(
        [{field: asset.get(field) for field in fields} for asset in assets],
        key=lambda row: row['name'],
    )
    if any(type(row['id']) is not int or type(row['size']) is not int or row['size'] <= 0
           or row['state'] != 'uploaded'
           or not re.fullmatch(r'sha256:[0-9a-f]{64}', row['digest'] or '') for row in rows):
        raise ValueError('Release assets lack valid IDs, sizes or SHA-256 digests')
    if len(rows) >= 100:
        raise ValueError('Release asset list exceeds the supported single page')
    ref = api(f'repos/{REPO}/git/ref/tags/{tag}')['object']
    while ref['type'] == 'tag':
        ref = api(f'repos/{REPO}/git/tags/{ref["sha"]}')['object']
    if ref['type'] != 'commit' or not re.fullmatch(r'[0-9a-f]{40}', ref['sha']):
        raise ValueError('Release tag must resolve to an exact commit')
    snapshot = {'release_id': release['id'], 'tag': tag, 'source_commit': ref['sha'], 'assets': rows}
    encoded = json.dumps(snapshot, sort_keys=True, separators=(',', ':')).encode()
    return snapshot, hashlib.sha256(encoded).hexdigest()

def stable_contract(tag,manifest,source_commit):
    validate(manifest)
    if tag != manifest['distribution_id']+'-'+manifest['image_version'] or manifest['build_commit'] != source_commit:
        raise ValueError('Tag or source commit differs from the candidate manifest')
    if manifest['guest_interface_abi'] != 1 or manifest['minimum_wsx_core_version'] is None:
        raise ValueError('Stable release requires a supported Guest ABI and explicit minimum Core')
    if not isinstance(manifest.get('desktop_compatibility'),dict):
        raise ValueError('Stable release requires the declared Guest desktop protocol')
    if manifest.get('source_delivery_schema') != 2:
        raise ValueError('Stable release requires public shared source delivery')

def stable_manifest(directory,tag,source_commit,snapshot):
    manifest=validate(json.loads((directory/'manifest.json').read_text()))
    stable_contract(tag,manifest,source_commit)
    marker=json.loads((directory/'completion.json').read_text())
    validate_completion(manifest,marker)
    required=asset_names(manifest)
    if set(a['name'] for a in snapshot['assets']) != set(required)|{'completion.json'}:
        raise ValueError('Release asset set differs from completion')
    for row in snapshot['assets']:
        file=directory/row['name']
        if not file.is_file() or file.is_symlink() or file.stat().st_size != row['size'] or 'sha256:'+digest(file) != row['digest']:
            raise ValueError('Downloaded release asset mismatch: '+row['name'])
        if row['name'] != 'completion.json' and marker['assets'][row['name']] != {'size':row['size'],'sha256':row['digest'][7:]}:
            raise ValueError('Completion entry does not match actual release asset')
    expected=''.join(f'{digest(directory/name)}  {name}\n' for name in required if name != 'SHA256SUMS')
    if (directory/'SHA256SUMS').read_text() != expected or json.loads((directory/'validation.json').read_text()) != manifest['validation']:
        raise ValueError('SHA256SUMS or validation report mismatch')
    sources=json.loads((directory/'sources.json').read_text())
    if sources.get('component_source_delivery', {}).get('schema_version') != 2:
        raise ValueError('Expected public shared source delivery metadata')
    if required_assets(directory,sources) != list(source_asset_names(manifest)):
        raise ValueError('Source delivery payload does not match manifest')
    check_public_source_delivery(directory,sources)
    return manifest

def require_approval_configuration():
    path = f'repos/{REPO}/environments/stable-release'
    environment = api(path)
    if not any(rule['type'] == 'required_reviewers' and rule.get('prevent_self_review')
               and rule.get('reviewers') for rule in environment['protection_rules']):
        raise ValueError('Configure required stable-release reviewers and prevent self-review')
    policy = environment.get('deployment_branch_policy') or {}
    if not policy.get('custom_branch_policies'):
        raise ValueError('Configure an explicit stable-release branch policy')
    policies = api(path + '/deployment-branch-policies?per_page=100')
    rules = policies['branch_policies']
    if policies['total_count'] != 1 or len(rules) != 1 or (
        rules[0].get('name'), rules[0].get('type', 'branch')
    ) != ('main', 'branch'):
        raise ValueError('stable-release must allow only the main branch')
    if api(f'repos/{REPO}/branches/main').get('protected') is not True:
        raise ValueError('Protect the main branch before enabling stable promotion')


def review(tag, archive_sha, manifest_sha, actor):
    snapshot, fingerprint = release_snapshot(tag)
    source_commit = snapshot['source_commit']
    with tempfile.TemporaryDirectory(prefix='wsx-promotion-') as temporary:
        directory = Path(temporary)
        subprocess.run(
            ['gh', 'release', 'download', tag, '--repo', REPO, '--dir', temporary],
            check=True,
        )
        manifest = stable_manifest(directory, tag, source_commit, snapshot)
        if archive_sha != manifest['sha256'] or manifest_sha != digest(directory / 'manifest.json'):
            raise ValueError('Acceptance hashes do not match the candidate archive and manifest')
        if release_snapshot(tag)[1] != fingerprint:
            raise ValueError('Release changed while verifying')

    acceptance = {
        'attested_by': actor,
        'attested_at_utc': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'archive_sha256': archive_sha,
        'manifest_sha256': manifest_sha,
        'stages': {stage: 'passed' for stage in (
            'wsl_boot', 'account_initialization', 'gpu_first_frame', 'desktop_input', 'normal_stop',
        )},
    }
    return {
        'tag': tag,
        'source_commit': source_commit,
        'snapshot_sha256': fingerprint,
        'minimum_wsx_core_version': manifest['minimum_wsx_core_version'],
        'manual_attestation': acceptance,
    }


def promote(tag, expected_snapshot):
    require_approval_configuration()
    snapshot, fingerprint = release_snapshot(tag)
    if fingerprint != expected_snapshot:
        raise ValueError('Release differs from the approved snapshot')
    path = f'repos/{REPO}/releases/{snapshot["release_id"]}'
    subprocess.run(
        ['gh', 'api', '--method', 'PATCH', path, '-F', 'prerelease=false'],
        check=True, stdout=subprocess.DEVNULL,
    )
    result = api(path)
    if result.get('tag_name') != tag or result.get('draft') is not False or result.get('prerelease') is not False:
        raise ValueError('Promotion read-back failed; inspect the release before retrying')
    print(f'Stable release promoted: {tag}')


def sha256_arg(value):
    if not re.fullmatch(r'[0-9a-f]{64}', value):
        raise argparse.ArgumentTypeError('Expected a lowercase SHA-256 digest')
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    review_parser = commands.add_parser('review')
    review_parser.add_argument('--tag', required=True)
    review_parser.add_argument('--archive-sha', required=True, type=sha256_arg)
    review_parser.add_argument('--manifest-sha', required=True, type=sha256_arg)
    review_parser.add_argument('--check-approval', action='store_true')
    promote_parser = commands.add_parser('promote')
    promote_parser.add_argument('--tag', required=True)
    promote_parser.add_argument('--expected-snapshot', required=True, type=sha256_arg)
    args = parser.parse_args()

    if args.command == 'promote':
        promote(args.tag, args.expected_snapshot)
        return
    if args.check_approval:
        require_approval_configuration()
    actor = os.environ['GITHUB_ACTOR']
    if not actor.strip():
        raise ValueError('An authenticated workflow actor is required')
    report = review(args.tag, args.archive_sha, args.manifest_sha, actor)
    with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
        for key in ('source_commit', 'snapshot_sha256'):
            print(f'{key}={report[key]}', file=output)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
