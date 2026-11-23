#!/usr/bin/env python3
"""Fetch immutable component archives and verify pinned content hashes."""
import argparse
import hashlib
from pathlib import Path
import subprocess

from source_support import component_pins, PROFILE_COMPONENTS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--profile', choices=PROFILE_COMPONENTS, default='omarchy')
    args = parser.parse_args()
    pins = component_pins(Path(__file__).resolve().parents[1], args.profile)
    args.output.mkdir(parents=True, exist_ok=True)
    for name, pin in pins.items():
        target = args.output/(name+'.archive')
        if not target.exists():
            partial = target.with_suffix('.partial')
            subprocess.run(['curl', '--fail', '--location', '--retry', '2', '--connect-timeout', '20',
                            '--max-time', '300', '--output', str(partial), pin['url']], check=True)
            with partial.open('rb') as stream:
                actual = hashlib.file_digest(stream, 'sha256').hexdigest()
            if actual != pin['sha256']:
                raise ValueError('Source content hash mismatch; retained partial: ' + name)
            partial.rename(target)
        with target.open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != pin['sha256']:
                raise ValueError('Cached source hash mismatch: ' + name)
        print(name, pin['sha256'], flush=True)


if __name__ == '__main__':
    main()
