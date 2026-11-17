#!/usr/bin/env python3
"""Stable upstream release selection; no publication side effects."""
import argparse
import json
import re
import subprocess

STABLE = re.compile(r"v?(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\Z")


def version(tag):
    match = STABLE.fullmatch(tag)
    if not match:
        raise ValueError(f"Unsupported stable version: {tag!r}")
    return tuple(map(int, match.groups()))


def select(releases, requested=None):
    candidates = [r for r in releases if not r.get('draft', True)
                  and not r.get('prerelease', True)
                  and STABLE.fullmatch(r.get('tag_name', ''))]
    if requested:
        wanted = version(requested)
        candidates = [r for r in candidates if version(r['tag_name']) == wanted]
    if not candidates:
        raise ValueError('No matching official stable Release; no tag fallback')
    return max(candidates, key=lambda r: version(r['tag_name']))


def gh(*args):
    return json.loads(subprocess.check_output(['gh', 'api', *args], text=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version')
    args = parser.parse_args()
    repo = 'omacom/omarchy'
    pages = gh('--paginate', '--slurp', f'repos/{repo}/releases?per_page=100')
    release = select([r for page in pages for r in page], args.version)
    tag = release['tag_name']
    # Resolve the selected Release tag, including annotated tags, to a commit.
    commit = gh(f'repos/{repo}/commits/{tag}')['sha']
    if not re.fullmatch(r'[0-9a-f]{40}', commit):
        raise ValueError('Invalid upstream commit')
    print(json.dumps({'repository': repo, 'release_id': release['id'],
                      'upstream_release': tag, 'upstream_commit': commit,
                      'release_url': release['html_url']}, indent=2))


if __name__ == '__main__':
    main()
