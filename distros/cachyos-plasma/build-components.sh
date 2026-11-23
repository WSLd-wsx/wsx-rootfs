#!/bin/bash
# Build the paired private runtime in the pinned, disposable Arch builder.
set -euo pipefail
cd /workspace
read -r arch_snapshot < distros/cachyos-plasma/arch-snapshot
printf 'Server = %s$repo/os/$arch\n' "$arch_snapshot" > /etc/pacman.d/mirrorlist
sed -i '/^\[options\]$/a DisableDownloadTimeout' /etc/pacman.conf

retry_package_operation() {
    local delay
    for delay in 5 10 20 40; do
        if "$@"; then
            return 0
        fi
        printf 'pacman failed, retrying in %s seconds using the existing package cache\n' "$delay" >&2
        sleep "$delay"
    done
    "$@"
}

# Bootstrap the downloader from the same signed snapshot. Bound the download
# phase separately so a hard timeout cannot interrupt a package installation.
retry_package_operation timeout --kill-after=15s 5m pacman -Syuw --noconfirm --needed archlinux-keyring aria2
retry_package_operation pacman -Su --noconfirm --needed archlinux-keyring aria2

# pacman supplies a .part destination and promotes it only after aria2 succeeds.
# Keep aria2's control file on failure so the next attempt resumes its pieces.
sed -i '/^\[options\]$/a XferCommand = /usr/bin/timeout --kill-after=15s 5m /usr/bin/aria2c --no-conf --continue=true --auto-file-renaming=false --file-allocation=none --console-log-level=warn --summary-interval=0 --connect-timeout=20 --timeout=60 --max-tries=5 --retry-wait=5 --max-file-not-found=1 --max-connection-per-server=4 --min-split-size=1M --split=4 --dir=/ --out=%o %u' /etc/pacman.conf

mapfile -t dependencies < distros/cachyos-plasma/build-dependencies.txt
if [[ -n ${CCACHE_DIR:-} ]]; then
    dependencies+=(ccache)
fi
retry_package_operation pacman -S --noconfirm --needed "${dependencies[@]}"
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
