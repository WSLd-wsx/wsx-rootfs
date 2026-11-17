#!/usr/bin/env python3
"""Export a review-only source snapshot without unresolved imports or Git history."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = frozenset('distros/cachyos-plasma/upstream/' + name for name in
                     ('netinstall.yaml',))


def prepare(destination):
    destination = destination.resolve()
    if destination.is_relative_to(ROOT) or destination.exists():
        raise ValueError('Use a new dedicated directory outside the repository')
    destination.mkdir(parents=True)
    names = subprocess.check_output(['git', 'ls-files', '-co', '--exclude-standard', '-z'], cwd=ROOT).decode().split('\0')
    deleted = set(filter(None, subprocess.check_output(['git', 'ls-files', '-d', '-z'], cwd=ROOT).decode().split('\0')))
    omitted = EXCLUDED | deleted
    records = []
    archive_path = destination/'wsx-rootfs-source-preview.tar.gz'
    with tarfile.open(archive_path, 'w:gz') as archive:
        for name in sorted(set(filter(None, names)) - omitted):
            path = ROOT/name
            if (path.is_symlink() or not path.is_file() or '.git' in Path(name).parts
                    or not path.resolve().is_relative_to(ROOT)):
                raise ValueError('Unsafe source snapshot entry: ' + name)
            data = path.read_bytes()
            info = archive.gettarinfo(str(path), arcname='wsx-rootfs-source-preview/' + name)
            info.uid = info.gid = 0
            info.uname = info.gname = ''
            info.mtime = 0
            with path.open('rb') as stream:
                archive.addfile(info, stream)
            records.append(dict(path=name, sha256=hashlib.sha256(data).hexdigest(), size=len(data)))
    manifest = dict(schema_version=1, base_commit=subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        scope='Current working files, without Git history, remote assets or logs',
        publication_approved=False, runnable_checkout=True,
        limitations=['Source snapshot; remote workflows and image distribution remain separately gated',
                     'No original repository history or tags may be copied into a public candidate',
                     'History filtering and remote ref changes require separate review'],
        excluded=sorted(omitted), files=records,
        archive_sha256=hashlib.sha256(archive_path.read_bytes()).hexdigest())
    (destination/'source-scope.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps(dict(directory=str(destination), files=len(records), excluded=len(omitted),
                          publication_approved=False, runnable_checkout=True)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    prepare(parser.parse_args().destination)
