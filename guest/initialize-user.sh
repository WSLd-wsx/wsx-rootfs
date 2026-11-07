#!/bin/bash
set -euo pipefail
mkdir -p "$HOME/.local/share" "$HOME/.local/bin" "$HOME/.config/omarchy/themes"
ln -sfn /usr/share/omarchy "$HOME/.local/share/omarchy"
install -m 0755 /usr/lib/wsx/runtime/session/wsx-launch-app "$HOME/.local/bin/wsx-launch-app"
mkdir -p "$HOME/Downloads" "$HOME/Pictures" "$HOME/Videos" "$HOME/Projects"
mkdir -p "$HOME/.config/omarchy/branding" "$HOME/.config/btop/themes"
cp /usr/share/omarchy/icon.txt "$HOME/.config/omarchy/branding/about.txt"
cp /usr/share/omarchy/logo.txt "$HOME/.config/omarchy/branding/screensaver.txt"
printf 'include "/usr/share/omarchy/default/xcompose"\n' > "$HOME/.XCompose"
OMARCHY_THEME_HEADLESS=1 omarchy-theme-set 'Tokyo Night'
ln -sfn "$HOME/.local/state/omarchy/current/theme/btop.theme" "$HOME/.config/btop/themes/current.theme"
xdg-user-dirs-update --set TEMPLATES "$HOME"
xdg-user-dirs-update --set PUBLICSHARE "$HOME"
xdg-user-dirs-update --set DESKTOP "$HOME"
mkdir -p "$HOME/.local/state/omarchy/migrations"
# Fresh images already contain this release. Historical disk/boot migrations
# (including Limine) must not be replayed on WSL during initialization.
for migration in /usr/share/omarchy/migrations/*.sh; do
  touch "$HOME/.local/state/omarchy/migrations/$(basename "$migration")"
done

# WSX performed its scoped setup; skip upstream hardware/provisioning leaves.
omarchy-done mark finalize-user
