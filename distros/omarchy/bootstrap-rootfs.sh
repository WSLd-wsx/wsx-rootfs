#!/bin/bash
set -euo pipefail
cd /workspace
# The builder is ephemeral. All package installs retain Required signatures.
pacman -Syu --noconfirm --needed archlinux-keyring arch-install-scripts python curl gcc patch
pacman-key --init
# Do not inherit Docker image slimming or its sandbox workaround into a desktop.
# The privileged isolated builder supports normal pacman package extraction.
sed -i -E '/^[[:space:]]*NoExtract[[:space:]]*=/d; /^[[:space:]]*DisableSandboxFilesystem([[:space:]]|$)/d' /etc/pacman.conf
fingerprint=40DFB630FF42BCFFB047046CF0134EE680CAC571
pacman-key --recv-keys "$fingerprint" --keyserver hkps://keys.openpgp.org
pacman-key --finger "$fingerprint"
pacman-key --lsign-key "$fingerprint"
cat >> /etc/pacman.conf <<'EOF'

[omarchy]
SigLevel = Required DatabaseOptional
Server = https://pkgs.omarchy.org/stable/$arch
EOF
pacman -Sy --noconfirm
pacman-conf > /output/rootfs-repositories.conf
pacman -Sl > /output/repository-packages.txt
mapfile -t packages < distros/omarchy/rootfs-packages.txt
mkdir /output/rootfs
pacstrap -c /output/rootfs "${packages[@]}"

pacman -Q > /output/build-packages.txt
pacman-conf > /output/build-repositories.conf
