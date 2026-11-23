#!/bin/bash
# Build the paired private runtime in the pinned, disposable Arch builder.
set -euo pipefail
cd /workspace
read -r arch_snapshot < distros/cachyos-plasma/arch-snapshot
printf 'Server = %s$repo/os/$arch\n' "$arch_snapshot" > /etc/pacman.d/mirrorlist
pacman -Syu --noconfirm --needed archlinux-keyring
mapfile -t dependencies < distros/cachyos-plasma/build-dependencies.txt
if [[ -n ${CCACHE_DIR:-} ]]; then
    dependencies+=(ccache)
fi
pacman -S --noconfirm --needed "${dependencies[@]}"
if [[ -n ${CCACHE_DIR:-} ]]; then
    export CMAKE_C_COMPILER_LAUNCHER=ccache CMAKE_CXX_COMPILER_LAUNCHER=ccache
    ccache --zero-stats
    trap 'ccache --show-stats || true' EXIT
fi
pacman -Q > /output/build-packages.txt
pacman-conf > /output/build-repositories.conf
python scripts/check-provenance.py
python scripts/fetch-components.py /output/source-archives --profile cachyos-plasma
python scripts/build-components.py --profile cachyos-plasma --archives /output/source-archives --output /output/component-build
python scripts/assemble-source-components.py /output/component-build /output
python scripts/collect-component-materials.py /output
