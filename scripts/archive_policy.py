#!/usr/bin/env python3
"""Reuse a completed full archive check only for identical recipe and tool inputs."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

from contract import validate
from payload_contract import validate_completion
from release_access import api, download, releases

REPOSITORY = 'WSLd-wsx/wsx-rootfs'
REQUIRED = {'uid', 'gid', 'mode', 'symlink', 'hardlink', 'xattr', 'acl', 'capability', 'file_hash'}


def fingerprint(build):
    inputs = build['inputs']
    material = {
        'schema_version': 1,
        'distribution_id': inputs['distribution_id'],
        'architecture': inputs['architecture'],
        'upstream_commit': inputs.get('upstream_commit', inputs.get('installer_commit')),
        'recipe_files': inputs['recipe_files'],
        'tar_version': subprocess.check_output(['tar', '--version'], text=True).splitlines()[0],
        'zstd_version': subprocess.check_output(['zstd', '--version'], text=True).strip(),
    }
    if not material['upstream_commit'] or not material['recipe_files']:
        raise ValueError('Missing archive recipe inputs')
    encoded = json.dumps(material, sort_keys=True, separators=(',', ':')).encode()
    return hashlib.sha256(encoded).hexdigest()


def previous_evidence(repo, release, expected, distribution):
    if release.get('draft') is not False:
        return None
    items = api(f'repos/{repo}/releases/{release["id"]}/assets?per_page=100')
    assets = {item['name']: item for item in items}
    if len(assets) != len(items) or not {'manifest.json', 'completion.json', 'sources.json'} <= assets.keys():
        return None
    with tempfile.TemporaryDirectory(prefix='wsx-archive-evidence-') as temporary:
        data = {}
        for name in ('manifest.json', 'completion.json', 'sources.json'):
            target = Path(temporary)/name
            download(repo, assets[name], target)
            raw = target.read_bytes()
            if len(raw) != assets[name]['size'] or assets[name].get('digest') != 'sha256:'+hashlib.sha256(raw).hexdigest():
                raise ValueError('Prior metadata differs from server digest: '+name)
            data[name] = json.loads(raw)
    manifest = validate(data['manifest.json'])
    marker = data['completion.json']
    validate_completion(manifest, marker)
    if manifest['distribution_id'] != distribution or release['tag_name'] != distribution+'-'+manifest['image_version']:
        return None
    if set(assets) != set(marker['assets']) | {'completion.json'}:
        raise ValueError('Prior release has missing or unexpected assets')
    for name, recorded in marker['assets'].items():
        item = assets[name]
        if (item.get('state') != 'uploaded' or item.get('size') != recorded['size']
                or item.get('digest') != 'sha256:'+recorded['sha256']):
            raise ValueError('Prior asset identity differs: '+name)
    compression = data['sources.json'].get('compression', {})
    if (compression.get('verification_mode') != 'full' or compression.get('passed') is not True
            or compression.get('recipe_fingerprint') != expected
            or data['sources.json']['build_inputs'].get('build_identity') != manifest['build_identity']
            or fingerprint(data['sources.json']['build_inputs']) != expected
            or not REQUIRED.issubset(set(compression.get('verified', [])))):
        return None
    return {'tag': release['tag_name'], 'release_id': release['id'],
            'build_identity': manifest['build_identity'], 'archive_sha256': manifest['sha256'],
            'sources_sha256': marker['assets']['sources.json']['sha256']}


def select(repo, build):
    expected = fingerprint(build)
    plan = {'schema_version': 1, 'recipe_fingerprint': expected, 'mode': 'full', 'reason': 'no matching completed full verification'}
    try:
        if repo != REPOSITORY or api('repos/'+repo).get('private') is not True:
            raise ValueError('Archive evidence requires the approved private repository')
        for release in releases(repo):
            evidence = previous_evidence(repo, release, expected, build['inputs']['distribution_id'])
            if evidence:
                plan.update(mode='stream', reason='matching completed full verification', evidence=evidence)
                break
    except (ValueError, KeyError, OSError, subprocess.SubprocessError, json.JSONDecodeError) as error:
        plan.update(mode='full', reason='prior evidence unavailable or invalid: '+str(error))
    return plan


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True)
    parser.add_argument('--work', type=Path, required=True)
    args = parser.parse_args()
    result = select(args.repo, json.loads((args.work/'build.json').read_text()))
    destination = args.work/'archive-policy.json'
    if destination.exists():
        raise ValueError('Archive policy output already exists')
    destination.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))
