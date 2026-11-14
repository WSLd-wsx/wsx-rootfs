#!/usr/bin/env python3
"""Offline rootfs admission; never starts systemd, WSL or a GPU."""
import argparse
import json
from pathlib import Path
import subprocess
from archive import check_hygiene
from image_paths import resolve
from desktop_contract import declaration, CAPABILITIES
from check_guest_bootstrap import check as check_guest_bootstrap
p=argparse.ArgumentParser(description=__doc__);p.add_argument('root',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
root=a.root.resolve(strict=True)
check_hygiene(root)
protocol_contract = declaration(root)
bootstrap_reply = check_guest_bootstrap(root)
(a.output/'guest-bootstrap-v2-check.json').write_text(json.dumps(dict(scope='offline bootstrap capabilities only; no session or GPU execution', response=bootstrap_reply), indent=2)+'\n')
# Desktop protocol capability checks require the externally supplied adapter.
protocol_reply = {'status': 'not_run', 'reason': 'Adapter is supplied by the Host product build'}
(a.output/'guest-protocol-check.json').write_text(json.dumps(protocol_reply, indent=2)+'\n')
# A rolling repository must not silently replace the libraries used to compile
# the private stack between build and installation.
def package_versions(path):
    return dict(line.split(' ',1) for line in path.read_text().splitlines())
built=package_versions(a.output/'build-packages.txt')
installed=package_versions(a.output/'rootfs-packages.txt')
for name in built.keys() & installed.keys():
    if built[name] != installed[name]:
        raise ValueError('Build/rootfs package version mismatch: '+name)

required=['usr/share/applications/omarchy-browser.desktop','etc/skel/.config/mimeapps.list',
          'etc/skel/.config/hyprland-xdg-terminals.list','usr/lib/systemd/user/omarchy-fcitx5.service','usr/bin/omarchy','usr/bin/omarchy-launch-shell','usr/bin/localedef','usr/bin/systemctl','usr/bin/runuser','usr/bin/dbus-daemon',
          'usr/bin/pkexec','usr/bin/uwsm','usr/bin/Xwayland','usr/bin/foot',
          'usr/bin/pipewire','usr/bin/wireplumber','usr/lib/wsx/runtime/mesa/manifest.json',
          'usr/lib/wsx/runtime/venus/manifest.json','usr/lib/wsx/runtime/opaque-consumer/manifest.json']
for name in required:
    if not resolve(root,name).is_file():raise ValueError('Missing required Guest file: '+name)
links = {}
for path in root.rglob('*'):
    if not path.is_symlink(): continue
    relative=str(path.relative_to(root))
    target=resolve(root,relative)
    dynamic=target.relative_to(root).parts[:1] in [('proc',),('sys',),('dev',),('run',)]
    links[relative]={'target':str(target.relative_to(root)),'exists':target.exists(),'runtime_target':dynamic}
    if relative.startswith('usr/lib/wsx/') and not target.exists():
        raise ValueError('Dangling private runtime link: '+relative)
(a.output/'offline-details.json').write_text(json.dumps({'symlinks':links,'required_files':required,'guest_protocol':protocol_reply},indent=2)+'\n')
for path in (root/'usr/lib/wsx/runtime').rglob('*'):
    if not path.is_symlink() and path.stat().st_mode & 0o022:
        raise ValueError('Writable private runtime by group or others: '+str(path))
    if path.is_file() and not path.is_symlink() and path.open('rb').read(4)==b'\x7fELF':
        proc=subprocess.run(['chroot',str(root),'env',
             'LD_LIBRARY_PATH=/usr/lib/wsx/runtime/opaque-consumer/lib:/usr/lib/wsx/runtime/mesa/lib',
             'ldd','/'+str(path.relative_to(root))],capture_output=True,text=True)
        if 'not found' in proc.stdout+proc.stderr:
            raise ValueError('Unresolved private ELF dependency: '+str(path))
if list(root.glob('usr/lib/modules/**/*.ko*')):
    raise ValueError('Guest modules belong to core, not the rootfs')
if any(line.split(':')[1] not in ('!','!!','*') and not line.split(':')[1].startswith('!')
       for line in (root/'etc/shadow').read_text().splitlines()):
    raise ValueError('Image contains an unlocked account')
report=dict(build='passed',offline='passed',wsl_boot='not_run',gpu_first_frame='not_run',desktop='not_run',stability='not_run')
(a.output/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
