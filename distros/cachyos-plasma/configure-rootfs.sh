#!/bin/bash
# Configure a fresh WSL Guest; never run on a live distribution.
set -euo pipefail
cd /workspace
root=/output/rootfs
test -f "$root/etc/os-release"
# Preserve the distribution's own identity without overwriting Arch's package file.
rm -f "$root/etc/os-release"
install -m 0644 distros/cachyos-plasma/upstream/iso-os-release "$root/etc/os-release"
install -m 0644 distros/cachyos-plasma/upstream/iso-cachyos-release "$root/etc/cachyos-release"
python scripts/stage-cachyos.py "$root" /output/private
mkdir -p "$root/usr/share/licenses/wsx-components"
cp -a /output/image-materials/component-materials/notices/. "$root/usr/share/licenses/wsx-components/"
cp /etc/pacman.conf "$root/etc/pacman.conf"
cat > "$root/etc/wsl.conf" <<'CONFIG'
[boot]
systemd=true
[network]
generateResolvConf=true
generateHosts=true
[interop]
enabled=true
appendWindowsPath=false
[user]
default=root
CONFIG
install -d -m 0755 "$root/etc/sudoers.d" "$root/etc/polkit-1/rules.d"
printf '%%wheel ALL=(ALL:ALL) ALL\n' > "$root/etc/sudoers.d/10-wsx-wheel"
chmod 0440 "$root/etc/sudoers.d/10-wsx-wheel"
cat > "$root/etc/polkit-1/rules.d/49-wsx-admin.rules" <<'POLKIT'
// Select the requesting wheel user; authentication remains required.
polkit.addAdminRule(function(action, subject) {
    if (subject.isInGroup("wheel")) return ["unix-user:" + subject.user];
});
POLKIT
arch-chroot "$root" visudo -cf /etc/sudoers
arch-chroot "$root" passwd -l root
# The WSL VM owns its networking, boot and tmp mounts.
systemctl --root="$root" mask systemd-firstboot.service systemd-resolved.service systemd-networkd.service systemd-networkd.socket NetworkManager.service tmp.mount
systemctl --root="$root" set-default multi-user.target
printf 'en_US.UTF-8 UTF-8\n' > "$root/etc/locale.gen"
arch-chroot "$root" locale-gen
printf 'LANG=en_US.UTF-8\n' > "$root/etc/locale.conf"
arch-chroot "$root" pacman -Qkk > /output/package-files-check.txt || true
python scripts/sanitize-rootfs.py "$root"
python scripts/reset-cachyos-keyring.py "$root"
python scripts/write-image-license-map.py /output
python scripts/validate-cachyos.py "$root" /output
