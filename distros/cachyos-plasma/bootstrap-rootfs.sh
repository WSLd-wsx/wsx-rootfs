#!/bin/bash
# Bootstrap a signed generic x86-64 CachyOS Plasma candidate inside CI.
set -euo pipefail
cd /workspace
# Match the validated private KWin/Plasma 6.8.1 ABI using a signed Arch
# repository snapshot. Restore normal rolling mirrors inside the final image.
cp /etc/pacman.d/mirrorlist /tmp/wsx-rolling-mirrorlist
printf 'Server = https://archive.archlinux.org/repos/2026/10/28/$repo/os/$arch\n' > /etc/pacman.d/mirrorlist
pacman -Syu --noconfirm --needed archlinux-keyring arch-install-scripts python curl gcc
python3 /workspace/scripts/source-support.py wsx-cachyos-plasma
python - <<'PYTHON'
import hashlib, json
from pathlib import Path
source = Path('distros/cachyos-plasma/upstream')
lock = json.loads((source/'source.json').read_text())
for section in (lock['files'], lock['iso_identity']['files']):
    for name, expected in section.items():
        if hashlib.sha256((source/name).read_bytes()).hexdigest() != expected:
            raise ValueError('Official upstream input hash mismatch: ' + name)
PYTHON
pacman-key --init
sed -i -E '/^[[:space:]]*NoExtract[[:space:]]*=/d; /^[[:space:]]*DisableSandboxFilesystem([[:space:]]|$)/d' /etc/pacman.conf
fingerprint=882DCFE48E2051D48E2562ABF3B607488DB35A47
pacman-key --recv-keys "$fingerprint" --keyserver hkps://keys.openpgp.org
pacman-key --finger "$fingerprint"
pacman-key --lsign-key "$fingerprint"
# The generic repository is deliberately used on heterogeneous WSL hosts.
# Package signatures remain required and the official keyring is installed.
cat > /tmp/wsx-cachyos-repository.conf <<'REPOSITORY'
[cachyos]
SigLevel = Required DatabaseOptional
Server = https://mirror.cachyos.org/repo/$arch/$repo
REPOSITORY
python - <<'PY'
from pathlib import Path
p = Path('/etc/pacman.conf')
s = p.read_text()
if s.count('[core]') != 1 or s.count('[extra]') != 1 or '[cachyos]' in s:
    raise ValueError('Unexpected Arch repository configuration')
# Resolve packages available in the pinned Arch snapshot before falling back
# to CachyOS-only packages. A rolling CachyOS override of core packages can
# require a newer ABI than the snapshot provides.
p.write_text(s.rstrip() + '\n\n' + Path('/tmp/wsx-cachyos-repository.conf').read_text())
PY
pacman -Sy --noconfirm
pacman-conf > /output/rootfs-repositories.conf
pacman -Sl > /output/repository-packages.txt
mapfile -t packages < distros/cachyos-plasma/packages.txt
mkdir /output/rootfs
pacstrap -c /output/rootfs "${packages[@]}"
cp /tmp/wsx-rolling-mirrorlist /output/rootfs/etc/pacman.d/mirrorlist
pacman -Q > /output/build-packages.txt
pacman-conf > /output/build-repositories.conf
arch-chroot /output/rootfs pacman -Q > /output/rootfs-packages.txt
# Restore the normal CachyOS repository priority for the installed rolling
# system. This does not change the already captured build repository evidence.
python - <<'PY'
from pathlib import Path
p = Path('/etc/pacman.conf')
s = p.read_text()
repo = Path('/tmp/wsx-cachyos-repository.conf').read_text().strip()
if s.count(repo) != 1 or s.count('[core]') != 1:
    raise ValueError('Cannot restore CachyOS repository priority')
s = s.replace(repo, '', 1)
s = s.replace('[core]', repo + '\n\n[core]', 1)
p.write_text(s)
PY
printf '%s\n' 'Signed Plasma package bootstrap passed; Guest integration is still pending.'
