# WSL network presentation

Omarchy runs on WSL-owned links and generated DNS configuration. Its existing
`omarchy-network-status` command already reads the active route correctly; the
network panel instead derived its connection state from NetworkManager, which
is absent in this environment.

The adapter is enabled only by `WSX_WSL_NETWORK=1` in the production desktop
launcher. It polls the existing status command, displays the actual routed
interface, and uses the existing verbose command for address/gateway details.
The panel labels network management as Windows-owned and hides Guest DNS
provider controls. The first-run Wi-Fi setup prompt is skipped in this mode.
No addresses, routes, DNS servers, Windows radio settings or WSL boot settings
are changed. A mirrored Windows WLAN may appear as an Ethernet interface inside
WSL; the adapter does not manufacture a Guest Wi-Fi device or SSID.

`install.py OMARCHY_ROOT` verifies both source files against the before/after
hashes in `manifest.json` before applying either patch. It creates adjacent
backups, applies exact patches and verifies their results. Reapplication is
idempotent. Unknown upstream source versions reject explicitly and require a
reviewed adapter update. The launcher runs this check before desktop startup.

The current installation has been patched and QML syntax parsed. Actual WSL
mirrored mode, matching host/Guest IP and gateway, DNS resolution and HTTPS
connectivity are recorded in `desktop-integration-fix-01`. The updated panel's
appearance still requires a fresh production desktop lifetime.

Reference: [Microsoft WSL networking](https://learn.microsoft.com/windows/wsl/networking).

## Omarchy 4.0.6 profile

The installer selects a complete exact-hash match from the original profile or
`omarchy-4.0.6`. The latter preserves the upstream network panel changes while
retaining the WSL route observer and disabling Guest NetworkManager DNS edits.
A version-specific backup suffix prevents collision with the older source backup.
Unknown or mixed source revisions still reject before any file is changed.

The upgraded Omarchy session passes real shell IPC and menu activation on Iris Xe
with the existing opaque runtime and the corrected Guest module. Evidence is in
`artifacts/venus-rutabaga/omarchy-406-start-01`. Outside-session probes must set the
actual Wayland socket; inherited WSLg display variables do not address this shell.
