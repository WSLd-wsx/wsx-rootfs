#!/usr/bin/env python3
"""Offline admission of a CachyOS candidate; no real WSL or GPU is claimed."""
import argparse
import json
from pathlib import Path
import subprocess
from archive import check_hygiene
from image_paths import resolve
from source_support import kwin_lock
from desktop_contract import declaration
from check_guest_bootstrap import check as check_guest_bootstrap

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('root', type=Path)
p.add_argument('output', type=Path)
a = p.parse_args()
root = a.root.resolve(strict=True)
check_hygiene(root)
protocol_contract = declaration(root)
bootstrap_reply = check_guest_bootstrap(root)
(a.output/'guest-bootstrap-v2-check.json').write_text(json.dumps(dict(scope='offline bootstrap capabilities only; no session or GPU execution', response=bootstrap_reply), indent=2)+'\n')
protocol_reply = dict(scope='External desktop adapter supplied by the Host product build',
                      contract=protocol_contract)
(a.output/'guest-protocol-check.json').write_text(json.dumps(dict(scope='external adapter not exercised during image build',
    contract=protocol_contract,response=protocol_reply),indent=2)+'\n')
for destination, source in (('etc/os-release', 'iso-os-release'), ('etc/cachyos-release', 'iso-cachyos-release')):
    if (root/destination).is_symlink() or (root/destination).read_bytes() != (Path(__file__).resolve().parents[1]/'distros/cachyos-plasma/upstream'/source).read_bytes():
        raise ValueError('Missing or modified official CachyOS identity: '+destination)
keyring = root/'etc/pacman.d/gnupg'
if keyring.is_symlink() or not keyring.is_dir() or any(keyring.iterdir()) or keyring.stat().st_mode & 0o077:
    raise ValueError('Build-time pacman keyring was not cleared')
packages = dict(line.split(' ', 1) for line in (a.output/'rootfs-packages.txt').read_text().splitlines())
for name in ('cachyos-keyring', 'cachyos-mirrorlist', 'cachyos-settings', 'cachyos-kde-settings',
             'plasma-desktop', 'plasma-workspace', 'shelly', 'dolphin', 'konsole', 'polkit', 'sudo'):
    if name not in packages:
        raise ValueError('Missing required CachyOS package: '+name)
pin = kwin_lock(Path(__file__).resolve().parents[1])
for name, version in pin['packages'].items():
    if packages.get(name) != version:
        raise ValueError('Private KWin dependency version mismatch: '+name+' '+packages.get(name, '<missing>'))
required = ['etc/wsl.conf', 'etc/sudoers.d/10-wsx-wheel',
            'usr/bin/startplasma-wayland', 'usr/bin/Xwayland', 'usr/bin/runuser',
            'usr/bin/localedef', 'usr/bin/dbus-daemon', 'usr/bin/pkexec', 'usr/bin/pacman-key',
            'usr/share/pacman/keyrings/archlinux.gpg', 'usr/share/pacman/keyrings/cachyos.gpg',
            'usr/lib/wsx/initialize-user.sh', 'usr/lib/wsx/plasma-compat.json',
            'usr/lib/wsx/runtime/mesa/manifest.json', 'usr/lib/wsx/runtime/venus/manifest.json',
            'usr/lib/wsx/runtime/kwin-opaque/manifest.json', 'usr/lib/wsx/runtime/wsx-input-guest']
for path in required:
    if not resolve(root, path).is_file():
        raise ValueError('Missing required Guest file: '+path)
lock = json.loads((root/'usr/lib/wsx/plasma-compat.json').read_text())
if lock.get('cpu_architecture_level') != 'x86-64-v3' or lock.get('packages') != {name: packages[name] for name in ('kwin', 'plasma-workspace', 'qt6-base')}:
    raise ValueError('Plasma runtime compatibility lock differs from installed packages')
helper_path = f"opt/wsx/kwin-opaque-{pin['version']}/lib/libexec/plasma-setup-xwayland"
helper_link = root/helper_path
helper = resolve(root, helper_path)
if (not helper_link.is_symlink() or str(helper_link.readlink()) != '/usr/lib/plasma-setup-xwayland'
        or helper != root/'usr/lib/plasma-setup-xwayland' or not helper.is_file()
        or not helper.stat().st_mode & 0o111):
    raise ValueError('Private KWin Xwayland helper is missing or incompatible')
links = {}
for path in root.rglob('*'):
    if not path.is_symlink():
        continue
    relative = str(path.relative_to(root))
    target = resolve(root, relative)
    links[relative] = {'target': str(target.relative_to(root)), 'exists': target.exists()}
    if relative.startswith('usr/lib/wsx/') and not target.exists():
        raise ValueError('Dangling private runtime link: '+relative)
for path in (root/'usr/lib/wsx/runtime').rglob('*'):
    if not path.is_symlink() and path.stat().st_mode & 0o022:
        raise ValueError('Writable private runtime: '+str(path))
    if path.is_file() and not path.is_symlink() and path.open('rb').read(4) == b'\x7fELF':
        proc = subprocess.run(['chroot', str(root), 'env',
            'LD_LIBRARY_PATH=/usr/lib/wsx/runtime/kwin-opaque/lib:/usr/lib/wsx/runtime/mesa/lib',
            'ldd', '/'+str(path.relative_to(root))], capture_output=True, text=True)
        if 'not found' in proc.stdout+proc.stderr:
            raise ValueError('Unresolved private ELF dependency: '+str(path)+'\n'+proc.stdout+proc.stderr)
if list(root.glob('usr/lib/modules/**/*.ko*')):
    raise ValueError('Guest kernel modules belong to wsx-core')
if any(line.split(':')[1] not in ('!', '!!', '*') and not line.split(':')[1].startswith('!')
       for line in (root/'etc/shadow').read_text().splitlines()):
    raise ValueError('Image contains an unlocked account')
(a.output/'offline-details.json').write_text(json.dumps({'symlinks': links, 'required_files': required,'guest_protocol':protocol_reply}, indent=2)+'\n')
report = dict(build='passed', offline='passed')
(a.output/'validation.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report))
