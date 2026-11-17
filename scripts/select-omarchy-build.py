#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Resolve immutable Omarchy build inputs without mutating releases or tags."""
import json
import os
from pathlib import Path
import re
import subprocess

REPOSITORY = 'WSLd-wsx/wsx-rootfs'


def pages(endpoint):
    result = json.loads(subprocess.check_output(['gh', 'api', '--paginate', '--slurp', endpoint], text=True))
    if not isinstance(result, list) or any(not isinstance(page, list) for page in result):
        raise ValueError('Expected paginated GitHub results')
    return [item for page in result for item in page]


def revision_for(version, releases, refs, requested=0):
    if not re.fullmatch(r'(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)', version):
        raise ValueError('Expected a stable upstream version')
    if type(requested) is not int or requested < 0:
        raise ValueError('Revision must be nonnegative')
    pattern = re.compile(r'WSX-omarchy-' + re.escape(version) + r'-r([1-9][0-9]*)\Z')
    names = [item['tag_name'] for item in releases] + [item['ref'].removeprefix('refs/tags/') for item in refs]
    used = {int(match.group(1)) for name in names if (match := pattern.fullmatch(name))}
    return requested if requested else max(used, default=0) + 1


def main():
    root = Path(os.environ['WSX_RECIPE_DIR'])
    requested = os.environ.get('WSX_UPSTREAM_VERSION', '').strip()
    revision_text = os.environ.get('WSX_REVISION', '').strip()
    if revision_text and not re.fullmatch(r'[0-9]+', revision_text):
        raise ValueError('Revision must be a nonnegative integer')
    command = ['python3', str(root / 'scripts/releases.py')]
    if requested:
        command += ['--version', requested]
    upstream = json.loads(subprocess.check_output(command, text=True))
    version = upstream['upstream_release'].removeprefix('v')
    commit = upstream['upstream_commit']
    if not re.fullmatch(r'[0-9a-f]{40}', commit):
        raise ValueError('Invalid upstream release commit')
    releases = pages('repos/' + REPOSITORY + '/releases?per_page=100')
    refs = pages('repos/' + REPOSITORY + '/git/matching-refs/tags/?per_page=100')
    revision = revision_for(version, releases, refs, int(revision_text or '0'))
    output = Path(os.environ['GITHUB_OUTPUT'])
    with output.open('a') as stream:
        stream.write(f'version={version}\nrevision={revision}\nupstream_commit={commit}\n')
    print(json.dumps(dict(version=version, revision=revision, upstream_commit=commit)))


if __name__ == '__main__':
    main()
