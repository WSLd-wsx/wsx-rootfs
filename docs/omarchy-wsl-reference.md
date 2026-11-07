# Omarchy-wsl reference audit

The user identified [craigloewen-msft/Omarchy-wsl](https://github.com/craigloewen-msft/Omarchy-wsl)
as a reference used by the earlier successful build, and explicitly clarified
that its text-only product scope must not replace WSX's desktop scope.
The inspected commit and file hashes are in
[omarchy-wsl-reference.json](omarchy-wsl-reference.json).

Applicable mechanisms reused in the WSX recipe:

- Install reviewed Omarchy commands, configuration and theming assets instead
  of invoking the bare-metal ISO installer or Limine/Btrfs migration paths.
- Keep systemd enabled and select multi-user.target; the desktop starts through
  the owned WSX lifecycle interface rather than a boot-time display manager.
- Mask systemd-firstboot because WSX owns interactive identity initialization,
  and preserve WSL ownership of network/DNS by masking competing network units.
- Generate locale data, install Fastfetch branding, seed XDG user directories,
  theme state and the Btop theme link, and mark historical migrations applied
  only for the newly initialized user after scoped setup succeeds.

Deliberately not adopted:

- CLI-only package lists or any GUI-removal logic. WSX keeps Hyprland,
  Quickshell, Wayland/Xwayland, Polkit/PAM/user D-Bus, graphical apps, input,
  audio and its paired private Mesa/Venus/compositor stack.
- The baked user, empty password, NOPASSWD rule or fixed UID/OOBE assumptions.
  WSX initializes user credentials through its own protected control interface.
- Mutable latest base images, branch-tip source cloning, blanket package
  overwrite, ignored setup failures, or disabled pacman sandbox settings.
  The current remote builder installs signed packages with the existing sandbox.
- Blanket tmpfiles masking. WSX retains system/user runtime setup; any additional
  unit incompatibility must be demonstrated on its actual WSL image first.
- Its WSLg graphics launch path, which is not the independent WSX host path.

This reference does not prove that the newly built WSX rootfs boots or presents
on any hardware. It supplies applicable setup patterns, not GPU acceptance.
