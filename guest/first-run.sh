#!/bin/bash
# WSL session leaves from the pinned Omarchy first-run recipe. No hardware setup.
set -euo pipefail
if omarchy-done check first-run-user; then exit 0; fi
# Hyprland imports its actual display into the user manager before app services.
for ((attempt=0; attempt<100; attempt++)); do
  if systemctl --user show-environment | grep -q '^WAYLAND_DISPLAY='; then break; fi
  sleep 0.1
done
systemctl --user show-environment | grep -q '^WAYLAND_DISPLAY='
systemctl --user daemon-reload
systemctl --user enable --now omarchy-fcitx5.service
bash "$OMARCHY_PATH/install/user/first-run/gnome-theme.sh"
bash "$OMARCHY_PATH/install/user/first-run/gtk-primary-paste.sh"
omarchy-notification-wait
bash "$OMARCHY_PATH/install/user/first-run/welcome.sh"
omarchy-done mark first-run-user
