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


# Omarchy v4.5.0, commit ac2690cd7be4f47e4a255f5e2e78d904d436b068.
PROFILE_450 = {
    'shell/plugins/panels/network/Panel.qml': {
        'before': '8beba301a1d87db144543ad888226099c3dd1c2999f2a52106964b5851959adb',
        'after': '347f32a92a471ec7aab73130c99dfd6ed0143638f93f3bf7620bc76caa6505bc',
    },
    'install/user/first-run/wifi.sh': {
        'before': 'af88e353b3ff5d347a2399c9bcbe1be134540329362125aa29e5b2084d9eaa25',
        'after': 'e43b77b52028c4625c008eb548f18f36de1088e6483b5f03245a38a40f09485f',
    },
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('omarchy', type=Path)
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    profiles = [here, here / 'omarchy-4.0.6', here / 'omarchy-4.5.0']
    for profile in profiles:
        manifest = profile / 'manifest.json'
        if profile.name == 'omarchy-4.5.0':
            files = PROFILE_450
        elif manifest.is_file():
            files = json.loads(manifest.read_text())['files']
        else:
            continue
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
