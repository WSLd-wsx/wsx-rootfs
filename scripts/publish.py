#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Upload immutable candidate assets to a Draft; verify bytes before completion."""
from source_delivery import required_assets, check_public_source_delivery, check_private_source_delivery
from payload_contract import asset_names, source_asset_names
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import time
from contract import validate


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def gh(*args):
    return subprocess.check_output(['gh', *map(str, args)], text=True)


def api(path):
    return json.loads(gh('api', path))


def require_private_prerelease_repo(repo):
    if repo != 'WSLd-wsx/wsx-rootfs' or api('repos/' + repo).get('private') is not True:
        raise ValueError('Private test prereleases require the approved private repository')


def releases(repo):
    return [r for page in json.loads(gh('api', '--paginate', '--slurp',
            f'repos/{repo}/releases?per_page=100')) for r in page]


def download(repo, asset, target):
    for attempt in range(3):
        try:
            # Restart a failed read into a truncated caller-owned temporary file.
            # Never append bytes from separate HTTP responses.
            with target.open('wb') as output:
                subprocess.run(['gh', 'api', '-H', 'Accept: application/octet-stream',
                                f'repos/{repo}/releases/assets/{asset["id"]}'], stdout=output, check=True)
            return
        except subprocess.CalledProcessError:
            target.unlink(missing_ok=True)
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def verify_remote(repo, release, completion):
    assets = {a['name']: a for a in api(f'repos/{repo}/releases/{release["id"]}/assets?per_page=100')}
    with tempfile.TemporaryDirectory() as directory:
        for name, expected in completion['assets'].items():
            if Path(name).name != name or name not in assets:
                raise ValueError('Missing or invalid asset: ' + name)
            if assets[name]['size'] != expected['size']:
                raise ValueError('Remote size mismatch: ' + name)
            path = Path(directory) / name
            download(repo, assets[name], path)
            if digest(path) != expected['sha256']:
                raise ValueError('Remote hash mismatch: ' + name)


def verify_completion(repo, release, expected):
    assets = api(f'repos/{repo}/releases/{release["id"]}/assets?per_page=100')
    markers = [a for a in assets if a['name'] == 'completion.json']
    if len(markers) != 1:
        raise ValueError('Missing unique completion marker')
    with tempfile.TemporaryDirectory() as temporary:
        path = Path(temporary)/'completion.json'
        download(repo, markers[0], path)
        if json.loads(path.read_text()) != expected:
            raise ValueError('Completion identity or asset set differs')


def await_draft(repo, tag, attempts=10, delay=2):
    """Allow GitHub's release list to converge after successful creation."""
    for attempt in range(attempts):
        matches = [item for item in releases(repo) if item['tag_name'] == tag]
        if len(matches) > 1:
            raise ValueError('Ambiguous release tag')
        if matches:
            if not matches[0]['draft'] or matches[0]['prerelease']:
                raise ValueError('Expected a non-prerelease Draft')
            return matches[0]
        if attempt + 1 < attempts:
            time.sleep(delay)
    raise ValueError('New Draft is not visible yet; retry publication with the original payload')


def require_public_candidate(repo, manifest):
    metadata=api('repos/'+repo)
    if (repo!='WSLd-wsx/wsx-rootfs' or metadata.get('full_name')!=repo
            or metadata.get('private') is not False
            or manifest.get('distribution_id') not in ('WSX-omarchy','WSX-cachyos-plasma')
            or manifest.get('source_delivery_schema')!=2):
        raise ValueError('Public candidate requires the approved desktop repository and shared source delivery')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--private-prerelease', action='store_true')
    parser.add_argument('--private-draft', action='store_true')
    parser.add_argument('--public-prerelease', action='store_true')
    parser.add_argument('--existing-draft-id', type=int,
                        help='Recovery only: require this existing Draft and never create a replacement')
    args = parser.parse_args()
    if sum((args.private_prerelease, args.public_prerelease, args.private_draft)) > 1:
        raise ValueError('Conflicting publication modes')
    if args.private_prerelease or args.private_draft:
        require_private_prerelease_repo(args.repo)
    directory = args.directory.resolve()
    m = validate(json.loads((directory / 'manifest.json').read_text()))
    if args.public_prerelease:
        require_public_candidate(args.repo,m)
    prerelease=args.private_prerelease or args.public_prerelease
    required = asset_names(m)
    sources = json.loads((directory/'sources.json').read_text())
    delivered = required_assets(directory, sources)
    expected = list(source_asset_names(m))
    if delivered != expected:
        raise ValueError('Manifest/source delivery format mismatch')
    (check_private_source_delivery if args.private_prerelease or args.private_draft else check_public_source_delivery)(directory, sources)
    for name in required:
        path = directory / name
        if not path.is_file() or path.is_symlink():
            raise ValueError('Missing regular asset: ' + name)
    archive = directory / m['asset_name']
    if archive.stat().st_size != m['compressed_size'] or digest(archive) != m['sha256']:
        raise ValueError('Archive differs from manifest')
    expected_sums = ''.join(f'{digest(directory / name)}  {name}\n' for name in required if name != 'SHA256SUMS')
    if (directory / 'SHA256SUMS').read_text() != expected_sums:
        raise ValueError('SHA256SUMS must cover the complete payload in canonical order')
    if json.loads((directory / 'validation.json').read_text()) != m['validation']:
        raise ValueError('Validation report mismatch')
    completion = {'schema_version': 1, 'build_identity': m['build_identity'],
                  'assets': {name: {'size': (directory/name).stat().st_size,
                                    'sha256': digest(directory/name)} for name in required}}
    tag = m['distribution_id'] + '-' + m['image_version']
    matches = [r for r in releases(args.repo) if r['tag_name'] == tag]
    if args.existing_draft_id is not None and (len(matches) != 1
            or matches[0].get('id') != args.existing_draft_id or matches[0].get('draft') is not True):
        raise ValueError('Original Draft disappeared or changed; refusing to create a replacement')
    if len(matches) > 1:
        raise ValueError('Ambiguous release tag')
    if matches and matches[0]['prerelease'] and not prerelease:
        raise ValueError('Existing version is a prerelease; refusing to repurpose it')
    if matches and not matches[0]['draft'] and prerelease and not matches[0]['prerelease']:
        raise ValueError('Refusing to repurpose a stable release as a private test')
    if matches and not matches[0]['draft']:
        # Public versions can be checked, but never modified, even on retry.
        verify_remote(args.repo, matches[0], completion)
        verify_completion(args.repo, matches[0], completion)
        print('Public assets already match; no mutation performed')
        return
    if not matches:
        gh('release', 'create', tag, '--repo', args.repo, '--draft', '--target', m['build_commit'],
           '--title', tag, '--notes', 'Candidate only. Offline checks do not establish WSL/GPU acceptance.')
    release = matches[0] if matches else await_draft(args.repo, tag)
    assets = {a['name']: a for a in api(f'repos/{args.repo}/releases/{release["id"]}/assets?per_page=100')}
    if 'completion.json' in assets:
        verify_completion(args.repo, release, completion)
    # Preflight every existing asset before uploading anything.
    with tempfile.TemporaryDirectory() as temporary:
        for name in required:
            if name in assets:
                path = Path(temporary)/name
                download(args.repo, assets[name], path)
                if digest(path) != completion['assets'][name]['sha256']:
                    raise ValueError('Conflicting candidate asset; use a new revision: ' + name)
    for name in required:
        if name not in assets:
            gh('release', 'upload', tag, directory/name, '--repo', args.repo)
    verify_remote(args.repo, release, completion)
    with tempfile.TemporaryDirectory(prefix='wsx-completion-') as marker_directory:
        marker = Path(marker_directory) / 'completion.json'
        marker.write_text(json.dumps(completion, sort_keys=True, indent=2) + '\n')
        if 'completion.json' in assets:
            with tempfile.TemporaryDirectory() as temporary:
                remote = Path(temporary)/'completion.json'
                download(args.repo, assets['completion.json'], remote)
                if remote.read_bytes() != marker.read_bytes():
                    raise ValueError('Completion marker conflict')
        else:
            gh('release', 'upload', tag, marker, '--repo', args.repo)
        final = api(f'repos/{args.repo}/releases/{release["id"]}')
        if not final['draft']:
            raise ValueError('Release unexpectedly promoted by another actor')
        verify_remote(args.repo, final, {'assets': {'completion.json': {'size': marker.stat().st_size, 'sha256': digest(marker)}}})
    if prerelease:
        if args.private_prerelease:
            require_private_prerelease_repo(args.repo)
        else:
            require_public_candidate(args.repo,m)
            check_public_source_delivery(directory,sources)
        try:
            gh('release', 'edit', tag, '--repo', args.repo, '--prerelease', '--latest=false', '--draft=false')
        except subprocess.CalledProcessError:
            # A transient response may arrive after GitHub committed the edit.
            # Never retry a mutation until the actual release state is known.
            final = api(f'repos/{args.repo}/releases/{release["id"]}')
            if final.get('draft') is not False or final.get('prerelease') is not True:
                raise
            verify_remote(args.repo, final, completion)
            verify_completion(args.repo, final, completion)
        final = api(f'repos/{args.repo}/releases/{release["id"]}')
        if final.get('draft') is not False or final.get('prerelease') is not True:
            raise ValueError('Private prerelease state was not confirmed')
    print(final['html_url'])


if __name__ == '__main__':
    main()
