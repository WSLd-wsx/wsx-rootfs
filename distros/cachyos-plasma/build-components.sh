#!/bin/bash
# Build the paired private runtime in the pinned, disposable Arch builder.
set -euo pipefail
cd /workspace
printf 'Server = https://archive.archlinux.org/repos/2026/10/28/$repo/os/$arch\n' > /etc/pacman.d/mirrorlist
pacman -Syu --noconfirm --needed archlinux-keyring
mapfile -t dependencies < distros/cachyos-plasma/build-dependencies.txt
pacman -S --noconfirm --needed "${dependencies[@]}"
pacman -Q > /output/build-packages.txt
pacman-conf > /output/build-repositories.conf
python scripts/check-provenance.py
python scripts/fetch-components.py /output/source-archives
python scripts/build-components.py --profile cachyos-plasma --archives /output/source-archives --output /output/component-build
python scripts/assemble-source-components.py /output/component-build /output
python scripts/collect-component-materials.py /output
