# SPDX-License-Identifier: GPL-2.0-or-later
"""Mandatory protocol and runtime pairing for newly built desktop images.

A checked receipt snapshot decouples Linux image assembly from Windows binaries.
Core still verifies the actual runtime; this declaration is not GPU acceptance.
"""
import ast
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PIN_DIR = ROOT/'components/desktop-runtime'
CAPABILITIES = ['account.status','desktop.preflight','session.status','session.stop',
                'display.query','display.apply','lifecycle.cli-v1',
                'graphics.distro-device-view-v1','graphics.distro-input-view-v1']
FILES = ('guest-protocol.py','protocol-display.py','protocol-retirement.py','device-view.py','guest-profile.json')
EXPECTED = dict(schema_version=1, guest_protocol_major=1, guest_protocol_minor=0,
                lifecycle_abi=1, display_abi=1, sharing_path='opaque-v1',
                producer_abi=1, consumer_abi=2, retirement='guest-stop-v1')


def runtime_pin():
    pin = json.loads((PIN_DIR/'contract.json').read_text())
    required = set(EXPECTED) | {'minimum_wsx_core_version','runtime_receipt_sha256'}
    if set(pin) not in (required, required | {'guest_bootstrap_major'}):
        raise ValueError('Incomplete or unknown runtime protocol pin')
    if 'guest_bootstrap_major' in pin and (type(pin['guest_bootstrap_major']) is not int or pin['guest_bootstrap_major'] != 2):
        raise ValueError('Unsupported Guest bootstrap version')
    if any(type(pin[k]) is not type(v) or pin[k] != v for k,v in EXPECTED.items()):
        raise ValueError('Unsupported runtime protocol pin')
    minimum = pin['minimum_wsx_core_version']
    if not re.fullmatch(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)', minimum):
        raise ValueError('Invalid minimum Core version')
    if tuple(map(int,minimum.split('.'))) < (0,2,1):
        raise ValueError('Guest protocol requires Core 0.2.1 or newer')
    raw = (PIN_DIR/'verified-files.json').read_bytes()
    if hashlib.sha256(raw).hexdigest() != pin['runtime_receipt_sha256']:
        raise ValueError('Runtime receipt differs from protocol pin')
    files = json.loads(raw)
    if not isinstance(files,dict) or 'wsx-native-host.exe' not in files:
        raise ValueError('Incomplete runtime receipt')
    for name, entry in files.items():
        relative = Path(name)
        if not name or relative.is_absolute() or '..' in relative.parts or '\\' in name or ':' in name:
            raise ValueError('Unsafe runtime receipt path')
        if (set(entry) != {'bytes','sha256'} or type(entry['bytes']) is not int or entry['bytes'] <= 0
                or not re.fullmatch('[0-9a-f]{64}',entry['sha256'])):
            raise ValueError('Invalid runtime receipt entry')
    return pin, files


def packaged_profile(rootfs, require_bootstrap=False):
    rootfs = Path(rootfs)
    base = rootfs/'usr/lib/wsx'
    for name in FILES:
        path = base/name
        if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o022:
            raise ValueError('Guest protocol is not packaged with safe permissions: '+name)
    if require_bootstrap:
        for name in ('bootstrap-v2.py', 'adapter-store.py'):
            path = base/name
            if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o022:
                raise ValueError('Guest bootstrap is not packaged with safe permissions: '+name)
        tree = ast.parse((base/'bootstrap-v2.py').read_text())
        if not any(isinstance(node, ast.FunctionDef) and node.name == 'dispatch' for node in tree.body):
            raise ValueError('Guest bootstrap does not provide pinned dispatch')
    tree = ast.parse((base/'guest-protocol.py').read_text())
    declarations = [n.value for n in tree.body if isinstance(n, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == 'CAPABILITIES' for t in n.targets)]
    if len(declarations) != 1:
        raise ValueError('Guest protocol capability declaration is missing or ambiguous')
    actual = ast.literal_eval(declarations[0])
    if not isinstance(actual, list) or not set(CAPABILITIES).issubset(actual):
        raise ValueError('Packaged Guest does not provide required capabilities')
    for name in ('desktop.py', 'wsx-input-guest'):
        path = base/'runtime'/name
        if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o022:
            raise ValueError('Concurrent Guest component is missing or unsafe: '+name)
    if not (base/'runtime/wsx-input-guest').stat().st_mode & 0o111:
        raise ValueError('Guest input component is not executable')
    raw = (base/'guest-profile.json').read_bytes()
    profile = json.loads(raw)
    consumer = {'hyprland':'opaque-consumer','plasma':'kwin-opaque'}.get(profile.get('implementation'))
    if (profile.get('schema_version') != 1 or not consumer or profile.get('consumer') != consumer
            or set(profile.get('component_manifests',{})) != {'mesa','venus',consumer}):
        raise ValueError('Invalid packaged Guest profile')
    for name, expected in profile['component_manifests'].items():
        manifest = base/'runtime'/name/'manifest.json'
        if manifest.is_symlink() or hashlib.sha256(manifest.read_bytes()).hexdigest() != expected:
            raise ValueError('Packaged component profile mismatch: '+name)
    return hashlib.sha256(raw).hexdigest()


def declaration(rootfs, runtime_receipt=None, minimum_core=None):
    pin, files = runtime_pin()
    if bool(runtime_receipt) != bool(minimum_core):
        raise ValueError('Desktop pairing and minimum Core must be supplied together')
    if runtime_receipt:
        receipt = Path(runtime_receipt)
        if (minimum_core != pin['minimum_wsx_core_version'] or
                hashlib.sha256(receipt.read_bytes()).hexdigest() != pin['runtime_receipt_sha256']):
            raise ValueError('Explicit runtime pairing differs from the checked build pin')
        for name, entry in files.items():
            target = receipt.parent/name
            if target.stat().st_size != entry['bytes']:
                raise ValueError('Runtime size mismatch')
            with target.open('rb') as stream:
                if hashlib.file_digest(stream,'sha256').hexdigest() != entry['sha256']:
                    raise ValueError('Runtime hash mismatch')
    result = {k:v for k,v in pin.items() if k != 'minimum_wsx_core_version'}
    result.update(guest_profile_sha256=packaged_profile(rootfs, pin.get('guest_bootstrap_major') == 2), required_capabilities=CAPABILITIES)
    return result


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-pin', action='store_true', required=True)
    parser.parse_args()
    pin, files = runtime_pin()
    print(json.dumps(dict(protocol_pin=pin, receipt_files=len(files), hardware_acceptance=False)))
