#!/usr/bin/env python3
"""Apply the reviewed Omarchy WSL presentation adapter without changing networking."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('omarchy', type=Path)
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    profiles = [here, here / 'omarchy-4.0.6']
    for profile in profiles:
        manifest = profile / 'manifest.json'
        if not manifest.is_file():
            continue
        files = json.loads(manifest.read_text())['files']
        if all((args.omarchy / relative).is_file() and
               sha(args.omarchy / relative) in (hashes['before'], hashes['after'])
               for relative, hashes in files.items()):
            break
    else:
        raise RuntimeError('Omarchy source differs from all reviewed network adapters')
    # Select only a complete exact-match profile before changing any file.
    suffix = '.before-wsx-network' + ('' if profile == here else '-' + profile.name)
    for relative, hashes in files.items():
        target = args.omarchy / relative
        if sha(target) == hashes['after']:
            continue
        backup = target.with_name(target.name + suffix)
        if backup.exists():
            if sha(backup) != hashes['before']:
                raise RuntimeError('Existing backup differs: ' + str(backup))
        else:
            shutil.copy2(target, backup)
        subprocess.run(['patch', '--batch', '--fuzz=0', '-p1', '-d', str(args.omarchy),
                        '-i', str(profile / (target.name + '.patch'))], check=True)
        if sha(target) != hashes['after']:
            raise RuntimeError('Patched source hash mismatch: ' + relative)
    print('WSL shell adapter installed; IP addresses, routes and DNS unchanged.')


if __name__ == '__main__':
    main()
