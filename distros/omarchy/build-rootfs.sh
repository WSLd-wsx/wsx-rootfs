#!/bin/bash
set -euo pipefail
cd /workspace
test -f /output/rootfs/etc/os-release
commit=$(python -c 'import json; print(json.load(open("/output/build.json"))["upstream"]["upstream_commit"])')
curl --fail --location --retry 2 --max-time 300 "https://codeload.github.com/omacom/omarchy/tar.gz/$commit" -o /output/omarchy.tar.gz
mkdir /output/omarchy-source
tar -xzf /output/omarchy.tar.gz --strip-components=1 -C /output/omarchy-source
python vendor/wsx-proto/network/install.py /output/omarchy-source
mkdir -p /output/rootfs/usr/share/omarchy
cp -a /output/omarchy-source/. /output/rootfs/usr/share/omarchy/
mkdir -p /output/rootfs/etc/skel/.config
cp -a /output/omarchy-source/config/. /output/rootfs/etc/skel/.config/
# Install the fixed release's commands and login environment as a package would.
for command in /output/rootfs/usr/share/omarchy/bin/*; do
  name=$(basename "$command")
  test ! -e "/output/rootfs/usr/bin/$name"
  ln -s "../share/omarchy/bin/$name" "/output/rootfs/usr/bin/$name"
done
install -m 0644 /output/omarchy-source/etc/profile.d/omarchy.sh /output/rootfs/etc/profile.d/omarchy.sh
mkdir -p /output/rootfs/usr/share/uwsm/env.d
cp -a /output/omarchy-source/default/uwsm/env.d/. /output/rootfs/usr/share/uwsm/env.d/
cat > /output/rootfs/etc/skel/.bashrc <<'EOF'
source /usr/share/omarchy/default/bash/env-bootstrap
[[ $- == *i* ]] || return
source "$OMARCHY_PATH/default/bash/rc"
EOF
# No disk bootloader or ISO autostart belongs in a WSL Guest session.
rm -f /output/rootfs/etc/skel/.config/autostart/limine-snapper-notify.desktop
rm -f /output/rootfs/etc/skel/.config/autostart/print-applet.desktop
# Match the fixed source's desktop routing and input-method configuration.
install -m 0644 /output/omarchy-source/applications/omarchy-browser.desktop /output/rootfs/usr/share/applications/omarchy-browser.desktop
install -m 0644 /output/omarchy-source/applications/foot.desktop /output/rootfs/usr/share/applications/foot.desktop
install -m 0644 /output/omarchy-source/default/xdg-terminal-exec/hyprland-xdg-terminals.list /output/rootfs/etc/skel/.config/hyprland-xdg-terminals.list
install -m 0644 /output/omarchy-source/default/systemd/user/omarchy-fcitx5.service /output/rootfs/usr/lib/systemd/user/omarchy-fcitx5.service
cat > /output/rootfs/etc/skel/.config/mimeapps.list <<'EOF'
[Default Applications]
inode/directory=org.gnome.Nautilus.desktop
x-scheme-handler/http=chromium.desktop
x-scheme-handler/https=chromium.desktop
video/mp4=mpv.desktop
video/webm=mpv.desktop
video/x-matroska=mpv.desktop
EOF
# The compositor prepends OMARCHY_PATH/bin; adapt that entry explicitly and
# retain the original source for provenance, rather than relying on PATH order.
mkdir -p /output/rootfs/usr/share/wsx/upstream
cp /output/rootfs/usr/share/omarchy/bin/omarchy-provision-first-run /output/rootfs/usr/share/wsx/upstream/
install -m 0755 guest/first-run.sh /output/rootfs/usr/share/omarchy/bin/omarchy-provision-first-run
python scripts/stage-guest.py /output/rootfs /output/private
mkdir -p "/output/rootfs/usr/share/licenses/wsx-components"
cp -a /output/image-materials/component-materials/notices/. "/output/rootfs/usr/share/licenses/wsx-components/"
mkdir -p /output/rootfs/usr/share/fonts/omarchy
cp -a /output/omarchy-source/default/fonts/omarchy/. /output/rootfs/usr/share/fonts/omarchy/
cp /etc/pacman.conf /output/rootfs/etc/pacman.conf
cat > /output/rootfs/etc/wsl.conf <<'EOF'
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
EOF
cat > /output/rootfs/etc/sudoers.d/10-wsx-wheel <<'EOF'
%wheel ALL=(ALL:ALL) ALL
EOF
chmod 0440 /output/rootfs/etc/sudoers.d/10-wsx-wheel
mkdir -p /output/rootfs/etc/polkit-1/rules.d
cat > /output/rootfs/etc/polkit-1/rules.d/49-wsx-admin.rules <<'EOF'
// Select the requesting wheel user's identity; authentication is still required.
polkit.addAdminRule(function(action, subject) {
    if (subject.isInGroup("wheel")) return ["unix-user:" + subject.user];
});
EOF
chmod 0644 /output/rootfs/etc/polkit-1/rules.d/49-wsx-admin.rules
arch-chroot /output/rootfs visudo -cf /etc/sudoers
arch-chroot /output/rootfs passwd -l root
# Adapt the reference's WSL-owned boot/network pattern. Keep tmpfiles and all
# desktop/session infrastructure; this is not its CLI-only package profile.
systemctl --root=/output/rootfs mask systemd-firstboot.service systemd-resolved.service systemd-networkd.service systemd-networkd.socket NetworkManager.service tmp.mount
systemctl --root=/output/rootfs set-default multi-user.target
mkdir -p /output/rootfs/etc/fastfetch
cp /output/omarchy-source/etc/fastfetch/config.jsonc /output/rootfs/etc/fastfetch/config.jsonc
printf 'en_US.UTF-8 UTF-8\n' > /output/rootfs/etc/locale.gen
arch-chroot /output/rootfs locale-gen
printf 'LANG=en_US.UTF-8\n' > /output/rootfs/etc/locale.conf
arch-chroot /output/rootfs pacman -Q > /output/rootfs-packages.txt
arch-chroot /output/rootfs pacman -Qkk > /output/package-files-check.txt || true
# A failed package-file check is evidence, not automatic acceptance: the offline
# validator checks required executables, dependencies and intentional overlays.
python scripts/sanitize-rootfs.py /output/rootfs
python scripts/write-image-license-map.py /output
python scripts/validate-rootfs.py /output/rootfs /output
