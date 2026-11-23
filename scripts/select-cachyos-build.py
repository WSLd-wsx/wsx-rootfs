#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Select a CachyOS WSX build-date snapshot and an unused revision."""
from datetime import date, datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess

REPOSITORY = 'WSLd-wsx/wsx-rootfs'


def resolve_snapshot(requested, today=None):
    if requested:
        return requested
    today = today or datetime.now(timezone.utc).date()
    return f'{today.year}.{today.month}.{today.day}'


def select_revision(snapshot, releases, refs, requested=0):
    if not re.fullmatch(r'[0-9]{4}\.(?:[1-9]|1[0-2])\.(?:[1-9]|[12][0-9]|3[01])', snapshot):
        raise ValueError('Snapshot must be a date YYYY.M.D without zero padding')
    date(*map(int, snapshot.split('.')))
    if type(requested) is not int or requested < 0:
        raise ValueError('Revision must be nonnegative')
    pattern = re.compile(r'WSX-cachyos-plasma-' + re.escape(snapshot) + r'-r([1-9][0-9]*)\Z')
    names = [item['tag_name'] for item in releases] + [item['ref'].removeprefix('refs/tags/') for item in refs]
    used = {int(match.group(1)) for name in names if (match := pattern.fullmatch(name))}
    return requested if requested else max(used, default=0) + 1


def pages(endpoint):
    pages = json.loads(subprocess.check_output(['gh', 'api', '--paginate', '--slurp', endpoint], text=True))
    if not isinstance(pages, list) or any(not isinstance(page, list) for page in pages):
        raise ValueError('Expected paginated GitHub results')
    return [item for page in pages for item in page]


def main():
    snapshot = resolve_snapshot(os.environ.get('WSX_SNAPSHOT', '').strip())
    requested = os.environ.get('WSX_REVISION', '').strip()
    if requested and not re.fullmatch(r'[0-9]+', requested):
        raise ValueError('Revision must be a nonnegative integer')
    releases = pages('repos/' + REPOSITORY + '/releases?per_page=100')
    refs = pages('repos/' + REPOSITORY + '/git/matching-refs/tags/?per_page=100')
    revision = select_revision(snapshot, releases, refs, int(requested or '0'))
    with Path(os.environ['GITHUB_OUTPUT']).open('a') as stream:
        stream.write(f'snapshot={snapshot}\nrevision={revision}\n')
    print(json.dumps(dict(snapshot=snapshot, revision=revision)))


if __name__ == '__main__':
    main()
