#!/usr/bin/env python3
"""Prepare the pinned private KWin consumer without modifying a running desktop."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

HERE = Path(__file__).resolve().parent

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('candidate', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    receipt = json.loads((args.candidate / 'source.json').read_text())
    if receipt.get('upstream_version') != '6.8.1':
        raise ValueError('Expected pinned KWin 6.8.1')
    for name, expected in receipt['source_sha256'].items():
        if hashlib.sha256((args.candidate / 'source' / name).read_bytes()).hexdigest() != expected:
            raise ValueError('Pinned source mismatch: ' + name)
    args.output.mkdir(parents=True, exist_ok=False)
    source = args.output / 'source'
    shutil.copytree(args.candidate / 'source', source, symlinks=True)
    subprocess.run(['patch', '--batch', '--fuzz=0', '-p1', '-d', str(source),
                    '-i', str(HERE / 'kwin-opaque-consumer.patch')], check=True)
    adapter = source / 'src/wsx'
    adapter.mkdir(exist_ok=True)
    files = ['kwin-native-buffer.h', 'kwin-framebuffer.c', 'kwin-framebuffer.h', 'kwin-wayland.inc',
             'gbm-descriptor.c', 'gbm-descriptor.h', 'wsx-opaque-uapi.h']
    for name in files:
        shutil.copy2(HERE / name, adapter / name)
    shutil.copy2(HERE / 'wayland/wsx-opaque-buffer-v1.xml', adapter / 'wsx-opaque-buffer-v1.xml')
    (args.output / 'source.json').write_text(json.dumps({
        'upstream_version': '6.8.1', 'deployed': False,
        'inputs': {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest()
                   for name in files + ['kwin-opaque-consumer.patch', 'wayland/wsx-opaque-buffer-v1.xml']},
    }, indent=2) + '\n')

if __name__ == '__main__':
    main()
