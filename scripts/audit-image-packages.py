#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later OR Apache-2.0
"""Compare package and notice metadata from a decoded rootfs tar with sources.json.

This is package inventory evidence, not an OSI classification, complete source
correspondence, legal clearance, archive authenticity or hardware acceptance.
The caller must independently bind the decoded tar to the verified release.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path, PurePosixPath
import tarfile


def fields(data):
    result = {}
    key = None
    for line in data.decode('utf-8', 'strict').splitlines():
        if line.startswith('%') and line.endswith('%'):
            key = line[1:-1]
            if key in result:
                raise ValueError('Duplicate pacman field: ' + key)
            result[key] = []
        elif line and key:
            result[key].append(line)
    return result


def audit(archive, source_path):
    source_bytes = source_path.read_bytes()
    sources = json.loads(source_bytes)
    expected = sources['rootfs_packages']
    if not isinstance(expected, list) or not all(isinstance(x, str) for x in expected):
        raise ValueError('Invalid recorded package list')
    if len(expected) != len(set(expected)):
        raise ValueError('Duplicate recorded package')
    packages, notices, seen = {}, set(), set()
    with tarfile.open(archive, 'r:') as stream:
        for member in stream:
            name = member.name.removeprefix('./').rstrip('/')
            if PurePosixPath(name).is_absolute() or '..' in PurePosixPath(name).parts:
                raise ValueError('Unsafe archive entry: ' + name)
            if name.startswith('usr/share/licenses/') and not member.isdir():
                notices.add(name)
            if not name.startswith('var/lib/pacman/local/') or not name.endswith(('/desc', '/files')):
                continue
            if name in seen or not member.isfile() or member.size > 4000000:
                raise ValueError('Duplicate or unsafe package metadata: ' + name)
            seen.add(name)
            directory, kind = name.rsplit('/', 1)
            packages.setdefault(directory, {})[kind] = fields(stream.extractfile(member).read())
    rows = []
    for key, record in sorted(packages.items()):
        if set(record) != {'desc', 'files'}:
            raise ValueError('Incomplete package metadata: ' + key)
        desc = record['desc']
        if len(desc.get('NAME', [])) != 1 or len(desc.get('VERSION', [])) != 1:
            raise ValueError('Invalid package identity: ' + key)
        owned = [x for x in record['files'].get('FILES', [])
                 if x.startswith('usr/share/licenses/') and not x.endswith('/')]
        rows.append(dict(name=desc['NAME'][0], version=desc['VERSION'][0],
                         licenses=desc.get('LICENSE', []), url=desc.get('URL', []),
                         depends=desc.get('DEPENDS', []), provides=desc.get('PROVIDES', []),
                         notice_files=len(owned),
                         missing_notice_paths=[x for x in owned if x not in notices]))
    actual = {row['name'] + ' ' + row['version'] for row in rows}
    if len(actual) != len(rows):
        raise ValueError('Duplicate installed package identity')
    labels = collections.Counter(label for row in rows for label in row['licenses'])
    return dict(schema_version=1, sources_json_sha256=hashlib.sha256(source_bytes).hexdigest(),
                package_count=len(rows), recorded_package_count=len(expected),
                packages_missing_from_image=sorted(set(expected)-actual),
                packages_missing_from_record=sorted(actual-set(expected)),
                packages_without_license=[row['name'] for row in rows if not row['licenses']],
                packages_with_missing_notice_paths=[row for row in rows if row['missing_notice_paths']],
                license_labels=dict(sorted(labels.items())), packages=rows,
                scope='Pacman declarations and owned notice paths only; not source closure or license approval')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('decoded_tar', type=Path)
    parser.add_argument('sources_json', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Output already exists')
    result = audit(args.decoded_tar, args.sources_json)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True)+'\n')
    print(json.dumps({key: value for key, value in result.items() if key not in ('packages', 'license_labels')}))


if __name__ == '__main__':
    main()
