# CachyOS Plasma candidate

The user requests the official default KDE Plasma Wayland desktop and official
package manager, preserving the distribution's normal configuration except where
it conflicts with WSL. The official 26.04 installer changelog identifies Shelly
as the default GUI package manager, replacing Octopi:
https://wiki.cachyos.org/cachyos_basic/changelogs/gui_installer/

The official ISO source was inspected at commit
`3215497d2e8c5fea90e185affcf973dfa2cf790b`:
https://github.com/CachyOS/CachyOS-Live-ISO/tree/3215497d2e8c5fea90e185affcf973dfa2cf790b
Its live desktop package list is a reference, not proof of installed-system
configuration; compare it with the official installer before selecting packages.
CachyOS rolling snapshot version naming and trigger cadence remain undecided.

The historical binary import route is retired. The current workflow and local
source preflight fail explicitly because the complete pinned KWin source,
packaging patch set, build dependencies and executable paired recipe are missing.
No stock KWin package or historical archive is used as a fallback. Historical
Plasma evidence remains in the linked records and does not attest a future build.

The prototype Plasma launcher and its four guard tests are vendored byte-for-byte:
`vendor/wsx-proto/device-host/production/start-cachyos-plasma.py` SHA-256
`1a1f17086f16220884c09396709742433204cf855ed671f4d94b9a5e10bc4cf1` and
test SHA-256 `8d79f8551758138ba48a067360da658eedcf88405d0ec119aeb0a9ad2dfc8663`.
Reference repository commit `3199b15dd898d6033e255e6894411b4bb4cab816` is not
substituted for content hashes: the reference may contain working-tree changes.
The launcher is historical source, not directly installed: it hardcodes a user,
a local deployment profile and module loading, and enables the opaque path by
bundle presence. Adapt it to the versioned injected Guest interface before use.

The user authorized `2026.11.1-r1` as a one-time internal WSX build-date
Draft label, not an official upstream release or a permanent snapshot policy.
The preserved bootstrap/configuration code describes the prior candidate route;
the current manual workflow stops at source preflight. Current validation results
must be read from the actual Actions run; compilation does not prove a WSL or
GPU session. The private historical launcher is transformed in a disposable
stage to inject the initialized user, instance, DRM node, input port, audio and
sharing mode. It requests Plasma logout before retiring owned input and seat
processes and rejects an unavailable
opaque producer/consumer kernel ABI.

The pinned current official installer configuration is recorded under upstream/
with its hashes. The recipe keeps the selected Plasma apps and Shelly while
excluding WSL-inapplicable kernel, bootloader and hardware-management packages.
Rolling repository contents and the historical private component toolchain are
not frozen; exact installed package versions are recorded for traceability.

The actual private KWin executable advertises x86-64-v3; images containing it
must advertise that requirement and reject unsupported Guest CPUs. The tested
KWin was paired with Plasma 6.8.1 and Qt 6.12.0. The initial candidate builds
against the signed Arch 2026-10-28 repository snapshot, while retaining the
CachyOS repository; normal rolling Arch mirrors are restored in the image.
Offline validation and the Guest lifecycle gate reject mismatched KWin, Plasma
Workspace or Qt versions, including after an unsupported rolling update. This
is a scoped compatibility constraint, not proof of future package compatibility.

Image sanitization removes the entire build-time local pacman keyring, including
the builder's signing identity and private key. During first-user
initialization the Guest creates its own key and populates the installed Arch
and CachyOS keyrings, preserving signature verification for pacman and Shelly.
No reusable builder secret or generic password is placed in the image.
