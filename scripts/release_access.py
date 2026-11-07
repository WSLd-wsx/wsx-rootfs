#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Read and verify release assets for recipe selection and archive evidence."""
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
