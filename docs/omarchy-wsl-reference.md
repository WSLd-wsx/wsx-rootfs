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

## Omarchy 4.5.0 compatibility check

Official stable Release `v4.5.0` resolves to commit
`ac2690cd7be4f47e4a255f5e2e78d904d436b068`. At that commit,
`shell/plugins/panels/network/Panel.qml` has SHA-256
`8beba301a1d87db144543ad888226099c3dd1c2999f2a52106964b5851959adb`
and `install/user/first-run/wifi.sh` has SHA-256
`af88e353b3ff5d347a2399c9bcbe1be134540329362125aa29e5b2084d9eaa25`.
Neither matches the reviewed 4.0.6 profile. An isolated dry run of its Panel
patch rejected four of eight hunks with fuzz disabled. The separately reviewed
4.5.0 candidate below uses its own exact-hash profile; no desktop acceptance is
implied.

### Version-specific adapter candidate

The 4.5.0 network adapter uses the fixed upstream commit and source hashes above.
The WSX adapter derives from `prototypes/venus-rutabaga/network/install.py` at
prototype commit `3199b15dd898d6033e255e6894411b4bb4cab816`, working-tree
SHA-256 `40ed88fff12ce0b278eb25400970fb714dd5079349157d6a787b4608326c9392`.
Its 4.0.6 profile working-tree manifest, Panel patch and wifi patch SHA-256 are
`1d14fa0b6a6a542d0aebbad6875099c26b0aa1e7aad51bd074658671d4414305`,
`0cb79d53615f52103900af4b70d71ee84b9c41dbc56e8c3b0394c6d28fbf7a87`, and
`8e76cd1ddcc036256e065244bddd6b7a261dc6ca9780af1e8d3c84215f5d7e81`.
The 4.5.0 Panel's Model.js dependency has SHA-256
`1562b0752495f693ef8231148f5e6d99c375d120852e9c312a2b47067aa9a8fa`
and retains `parseNetworkStatus`. The adapted source and existing setup script
were checked offline for exact application, reapplication and shell syntax;
this is not WSL desktop, GPU, or hardware acceptance. The upstream source files
are retrieved by fixed commit; patch and installer bytes are recorded in the
source inventory and image snapshot.

Remote operations run `42482863720` built `wsx-omarchy-4.5.0-r1` from rootfs
commit `dbd40aa7d3518afd0c3f55545dcbcd1de7da7c63` and upstream commit
`ac2690cd7be4f47e4a255f5e2e78d904d436b068`. Its log records exact application of
both network patches. The existing Omarchy paired component image was admitted
by immutable digest `sha256:f258bf8678e43c6fb905cdee1f3a75648cb877c2e6e356dda771524df31880e1`;
no graphics component compilation was performed. The verified candidate is a
Draft with compressed rootfs SHA-256
`5d61831e6d4b30e9dc71e11201723a38b11be7b75f5e47f3303acb4f37330181`.
Build and offline validation passed; WSL boot, GPU first frame, desktop and
stability remain `not_run`. This is not hardware compatibility evidence.
