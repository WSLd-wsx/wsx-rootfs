#!/usr/bin/env python3
"""Remove ephemeral build identity from an isolated rootfs, never a live root."""
from pathlib import Path
import argparse
import shutil
p=argparse.ArgumentParser(description=__doc__);p.add_argument('root',type=Path);a=p.parse_args()
root=a.root.resolve(strict=True)
if str(root) in ('/','/output','/workspace') or not (root/'etc/os-release').exists():
    raise SystemExit('Refusing a non-rootfs cleanup target')
for line in Path('/proc/self/mountinfo').read_text().splitlines():
    mount=Path(line.split()[4].replace('\\040',' ')).resolve()
    if mount==root or root in mount.parents:
        raise SystemExit('Refusing cleanup while rootfs contains a live mount: '+str(mount))
for relative in ('proc','sys','dev','run','tmp','var/tmp','var/cache','var/log','root','home'):
    path=root/relative
    if path.is_symlink():raise SystemExit('Unexpected cleanup symlink: '+relative)
    if path.exists():
        for child in path.iterdir():
            if child.is_dir() and not child.is_symlink():shutil.rmtree(child)
            else:child.unlink()
for relative in ('etc/machine-id','var/lib/dbus/machine-id'):
    path=root/relative;path.unlink(missing_ok=True)
(root/'etc/machine-id').touch()
for path in (root/'etc/ssh').glob('ssh_host_*'):path.unlink()
for relative in ('etc/hostname','etc/resolv.conf','etc/hosts'):
    (root/relative).unlink(missing_ok=True)
# The trust databases contain public package keys; never retain builder secrets.
for relative in ('etc/pacman.d/gnupg/private-keys-v1.d','etc/pacman.d/gnupg/openpgp-revocs.d'):
    path=root/relative
    if path.exists():shutil.rmtree(path)
for path in (root/'etc/pacman.d/gnupg').glob('S.*'):path.unlink(missing_ok=True)
for relative in ('tmp','var/tmp'):(root/relative).chmod(0o1777)
