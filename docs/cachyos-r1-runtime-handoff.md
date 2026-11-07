# CachyOS r1 real-machine handoff (2026-11-01)

## Acceptance boundary

Draft `wsx-cachyos-plasma-2026.11.1-r1` was downloaded, verified against its
completion manifest, decompressed and imported into a separate WSL instance.
Archive SHA-256: `481b794cee452487e1da31eb796e5f5f3da6ad178b21944ccbd54c017e032488`.
On Iris Xe, Windows driver 31.0.101.5081 and WSL kernel
6.18.54.1-microsoft-standard-WSL2, the image's private Mesa 26.1.8, Venus 26.2.4
and KWin 6.8.1 displayed CachyOS Hello and the Plasma taskbar through the
independent native host. The cutoff records 107 successful presentations,
opaque-v1, staging disabled and no agent WSL/service restart. Initial output was
784x441; this is not 1600x900 acceptance or RTX regression coverage.

**The unmodified image did not pass first desktop startup.** The following
local test-instance corrections were required. The published archive is unchanged.
Application functionality, sustained stability, and stop/restart after successful
rendering remain unverified. Do not promote the Draft or rewrite its original
build/offline validation metadata based on this bounded result.

## Rootfs-owned work

| ID | Observed issue and local correction | Required implementation and acceptance | Status |
| --- | --- | --- | --- |
| RF-1 | The transient user runtime directory disappeared during a session retry, removing the KWin environment drop-in. KWin then selected a logind session that rejected device access. Enabling linger for the initialized user preserved the configuration in the successful retry. | Make user-manager/runtime lifetime explicit in initialization and session startup. Adopt a deliberate linger policy or keep configuration alive through an owned session; do not merely bake in a test-user path. Verify first start and full logout/restart preserve the intended instance-tagged environment. | Local workaround verified; recipe/session implementation pending |
| RF-2 | Private KWin requested `/opt/wsx/kwin-opaque-6.8.1/lib/libexec/plasma-setup-xwayland`, which was absent. The test linked that exact path to the version-locked `/usr/lib/plasma-setup-xwayland`. | Package or relocate the matching helper through the private runtime build/staging contract. Check executable paths and version compatibility offline, then launch a real Xwayland application. A link alone is not complete Xwayland acceptance. | Local path correction applied; build implementation and application acceptance pending |
| RF-3 | Loss of the instance drop-in caused the normal stop guard to reject logout. The seatd process was then killed by unit cleanup, leaving its socket. A subsequent start correctly refused to replace it. | Preserve session ownership evidence independently of ephemeral configuration and retire compositor before input/seat. Permit stale socket recovery only after proving ownership and absence of a live listener. Keep identity guards intact. | Failure preserved; automated recovery pending |

The diagnostic logout verified the exact compositor executable and instance
marker before requesting Plasma's normal logout. Native context 2 destruction
completed. The stale seatd socket was preserved only after no seatd process and
ECONNREFUSED were confirmed. This manual recovery is not product lifecycle
acceptance and must not become unconditional deletion or forced process cleanup.

## Core-owned work and shared boundary

| ID | Observation | Owner and required behavior | Status |
| --- | --- | --- | --- |
| CORE-1 | The image's render group was GID 987, while the actual render node had GID 992. KWin could not open renderD129. | Core discovers the exact instance's card/render siblings and authorizes the initialized user before starting the session. Use checked per-user device ACLs rather than fixed numeric groups or world-writable permissions. Rootfs supplies user identity through the Guest interface; do not bake the observed UID, GIDs or device names into the image. | Exact-instance ACL worked locally; reusable integration pending |
| CORE-2 | The Windows input companion exited after Guest logout. Retrying the same instance required another companion. | Core owns instance-bound input reconnection, duplicate-owner rejection and readiness ordering. Rootfs waits for the injected endpoint and reports failure without claiming input readiness. | Manual same-instance reconnection verified; automation pending |

The origin of the incorrect render-node group has not been proven; the observed
numeric mismatch is sufficient evidence of the admission failure, not proof of
which distro or udev rule changed it. No GPU allocation, modifier or native
admission check was relaxed in this trial.

## Evidence and follow-up

Raw evidence is retained in the sibling wsx-proto checkout under
`artifacts/venus-rutabaga/rootfs-cachyos-r1-start-01/`. That artifacts directory
is local and is not guaranteed to exist in a clone or CI. It contains result.json,
desktop.png, native.log, guest-journal.log, both KWin failure logs and launch/retry
logs. Digests below identify the captured evidence, not remotely published files.

| Evidence | SHA-256 |
| --- | --- |
| `result.json` | `c5e9c98797201ef22ea54bf286abdfa988e60f0dceb7d5acf01f86fcff1c6469` |
| `desktop.png` | `bfd261f4397b01f1b5baa582743e3596ffa13ea6be2e0ea6544436839fdadb4a` |
| `native.log` | `b852b0996a456f0def2515a60a61cd35086a281a6fcdf91a9e035f9a1afb1a9f` |
| `guest-journal.log` | `0b84b585369c093763a00662384230287fc046f7992e4a395aa57a1f01084712` |
| `kwin-first-failure.log` | `42a60d3804c1a2fa1b36d57e5581c89ff2bdd9993842a19a25e48bb478752215` |
| `kwin-second-failure.log` | `6a7a9d375c4e1077a47c6c7262196eb81db4f6c2d5ba31649741aec80a7a1062` |

Implement RF-1/RF-2/RF-3 in this repository, with provenance updates for any
vendored adapter changes. Coordinate CORE-1/CORE-2 with the runtime repository.
Build a new revision through Actions, keep it Draft, and test a fresh import
without manual corrections. Verify first frame, input, Xwayland, full logout,
repeat start and sustained rendering separately. Keep minimum core compatibility
unresolved until the reusable interface is actually verified.

The runtime-side ownership record is
[wsx-proto ROOTFS-HANDOFF.md](../../wsx-proto/prototypes/venus-rutabaga/device-host/production/ROOTFS-HANDOFF.md)
in the sibling checkout; that relative cross-repository link is local-only.
