#!/usr/bin/env python3
"""Export session code from a staged image, binding internal calls to its bundle.

The result is a build input, not an admitted or installed adapter. Image-owned
graphics, profile and account initialization remain in the image.
"""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

SOURCES = {
    'protocol.py': 'usr/lib/wsx/guest-protocol.py',
    'display.py': 'usr/lib/wsx/protocol-display.py',
    'retirement.py': 'usr/lib/wsx/protocol-retirement.py',
    'device-view.py': 'usr/lib/wsx/device-view.py',
    'wsx-guest.py': 'usr/bin/wsx-guest',
    'desktop.py': 'usr/lib/wsx/runtime/desktop.py',
}


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('Unexpected adapter source; cannot safely bind ' + old)
    return text.replace(old, new)


def transform(name, text):
    replacements = {
        'protocol.py': [
            ("'/usr/lib/wsx/protocol-retirement.py'", "str(Path(__file__).resolve().with_name('retirement.py'))"),
            ("'/usr/lib/wsx/protocol-display.py'", "str(Path(__file__).resolve().with_name('display.py'))"),
        ],
        'retirement.py': [("'/usr/bin/wsx-guest', 'stop'", "'/usr/bin/python3', '-I', str(Path(__file__).resolve().with_name('wsx-guest.py')), 'stop'")],
        'wsx-guest.py': [
            ("'/usr/lib/wsx/device-view.py'", "str(Path(__file__).resolve().with_name('device-view.py'))"),
            ("'/usr/lib/wsx/guest-protocol.py'", "str(Path(__file__).resolve().with_name('protocol.py'))"),
            ("'/usr/bin/wsx-guest','session'", "'/usr/bin/python3','-I',str(Path(__file__).resolve()),'session'"),
            ("str(RUNTIME/'desktop.py')", "str(Path(__file__).resolve().with_name('desktop.py'))"),
        ],
        'desktop.py': [("'/usr/lib/wsx/device-view.py'", "str(Path(__file__).resolve().with_name('device-view.py'))")],
    }
    for old, new in replacements.get(name, []):
        text = replace_once(text, old, new)
    ast.parse(text, filename=name)
    # These are code references that must never return to the image adapter.
    forbidden = ('/usr/bin/wsx-guest', '/usr/lib/wsx/guest-protocol.py',
                 '/usr/lib/wsx/protocol-display.py', '/usr/lib/wsx/protocol-retirement.py',
                 '/usr/lib/wsx/device-view.py')
    if any(value in text for value in forbidden):
        raise ValueError('Unbound image adapter reference in ' + name)
    return text


def export(image, output, implementation):
    image = Path(image).resolve(strict=True)
    output = Path(output)
    if output.exists() or output.is_symlink(): raise ValueError('Destination already exists')
    profile = json.loads((image / 'usr/lib/wsx/guest-profile.json').read_bytes())
    if profile.get('schema_version') != 1 or profile.get('implementation') != implementation:
        raise ValueError('Staged image desktop implementation does not match')
    prepared = {}
    source_hashes = {}
    for name, relative in SOURCES.items():
        source = image / relative
        if source.is_symlink() or not source.is_file() or not source.resolve(strict=True).is_relative_to(image):
            raise ValueError('Unsafe or missing staged adapter source: ' + relative)
        raw = source.read_bytes()
        if not raw or len(raw) > 2 * 1024 * 1024: raise ValueError('Invalid adapter source size: ' + name)
        source_hashes[name] = hashlib.sha256(raw).hexdigest()
        prepared[name] = transform(name, raw.decode('utf-8')).encode('utf-8')
    temporary = Path(tempfile.mkdtemp(prefix='.guest-adapter-', dir=output.parent))
    try:
        for name, raw in prepared.items(): (temporary / name).write_bytes(raw)
        os.rename(temporary, output)
    finally:
        if temporary.exists(): shutil.rmtree(temporary)
    return {'implementation': implementation, 'source_sha256': source_hashes,
            'output_sha256': {name: hashlib.sha256(raw).hexdigest() for name, raw in prepared.items()},
            'admitted': False, 'desktop_validated': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--implementation', choices=('hyprland', 'plasma'), required=True)
    args = parser.parse_args()
    print(json.dumps(export(args.image, args.output, args.implementation), sort_keys=True))


if __name__ == '__main__': main()
