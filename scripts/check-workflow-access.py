#!/usr/bin/env python3
"""Allow public source checks while keeping unapproved binary delivery private."""
import argparse
import json
import subprocess

REPOSITORY = 'WSLd-wsx/wsx-rootfs'


def authorize(repo, metadata, operation):
    if metadata.get('full_name') != repo or type(metadata.get('private')) is not bool:
        raise ValueError('Repository identity or visibility could not be verified')
    if operation == 'source-check':
        return 'Source checks are allowed; this does not authorize binary distribution.'
    if operation == 'component-build' and repo == REPOSITORY:
        return 'Approved component compilation; uploads require a verified private GHCR package.'
    if operation in ('omarchy-candidate','cachyos-candidate') and repo == REPOSITORY:
        return 'Approved desktop candidate build; public prerelease requires explicit publication mode and source checks.'
    if operation != 'binary-build':
        raise ValueError('Unknown workflow operation')
    if repo != REPOSITORY or metadata['private'] is not True:
        raise ValueError('Public source-only mode: binary builds, diagnostic bundles and publication '
                         'are not enabled. Run the source contract checks instead.')
    return 'Approved private binary build; payload and publication gates still apply.'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True)
    parser.add_argument('--operation', required=True, choices=('source-check', 'binary-build', 'component-build', 'omarchy-candidate', 'cachyos-candidate'))
    args = parser.parse_args()
    metadata = json.loads(subprocess.check_output(['gh', 'api', 'repos/' + args.repo]))
    print(authorize(args.repo, metadata, args.operation))
