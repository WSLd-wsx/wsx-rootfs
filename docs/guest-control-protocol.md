# WSX Guest control protocol 1.0

Status: implemented in source for Alpha evaluation, not released or accepted in a
newly built rootfs. This document owns the public control contract. The retained
[lifecycle CLI ABI 1](guest-abi.md) owns interactive initialization and attached
prepare/start. Host implementation details belong to wsld. No business daemon,
network service or general shell/file-execution endpoint is introduced.

## Transport, version and authority

Core invokes `/usr/bin/wsx-guest host-call` as root through the local WSL control
channel. One invocation accepts one UTF-8 JSON object on stdin and returns one
JSON object on stdout. Input and output are bounded to 1 MiB. Diagnostic messages
go to stderr. The desktop and its control tools still run as the initialized
ordinary user; root control is not authorization to run the desktop as root.
Passwords use the separate interactive initialization channel, never this JSON.

```json
{"protocol":"wsx-guest","major":1,"minor":0,"id":"request-1","operation":"capabilities","params":{}}
```

`id` is 1..96 ASCII letters, digits, underscores or hyphens. A successful response
has the same protocol, major and id, the Guest's supported minor, `ok:true` and
`result`. An error has `ok:false` and `error:{code,message,retryable}`. Malformed
input can return `id:null`; a caller must never accept that as its success.
Protocol errors use the JSON envelope even when the process exits zero; a failed
process or invalid envelope is a transport failure, never success. No automatic
fallback to a legacy adapter is permitted for a declared protocol image.

A major version changes semantics. A minor adds compatible optional fields or
capabilities. The request minor is the minimum understood contract being used;
a Guest rejects a higher minimum than it implements. An older Core accepts a
newer reply minor and ignores additional optional fields. Unknown operations and
required capabilities fail. Required behavior must not be hidden in an optional
field. The release compatibility declaration is a separately versioned, closed
schema; it is not an extensible wire envelope.

Core uses a fresh registration GUID/disk binding for each command. A session's
`instance` is the actual Native/Guest lifetime UUID, not the distro name or a
reusable memory handle. The caller resolves that instance from the corresponding
Host. Guest validates its root-owned descriptor; compositor PID, socket and
process start time are private adapter observations, never Host API contracts.

## Operations implemented for the current Alpha profile

| Operation | Parameters and result | Effect |
| --- | --- | --- |
| `capabilities` | Supported major/minor, operation names, lifecycle/display ABI | Discovery only; does not prove readiness, GPU compatibility or permission |
| `account.status` | Initialized ordinary user/UID/timezone, or `initialized:false` | Read only; never resets credentials |
| `desktop.preflight` | Verified release `contract`, `require_idle` (default true); acknowledged profile/graphics contract and account | Checks Guest-owned component bytes/package locks and optional seat admission |
| `session.status` | `instance`; state `starting/running/stopping/stopped/failed/unknown` and result | Current Guest observation; `running` alone is not first-frame or health evidence |
| `session.stop` | `instance`; `session_retired:true` only after ordered Guest cleanup, `gpu_retired:false` | Normal exact-session logout; no forced fallback, no Host/device teardown claim |
| `display.query` | `instance`; output snapshot below | Read only |
| `display.apply` | Snapshot-bound output/mode/scale request below | Apply through Guest's own compositor adapter, then verify readback |
| `lifecycle.cli-v1` | Capability naming the existing prepare/start/initialize CLI ABI | Reuses the verified attached startup and password channel |

Normal stop may wait at a safe point. An observation timeout is not permission
to kill logout, remove the seat or declare resources retired. Session stopped,
first frame, lock state, Native device removal and GPU/mapping drain are separate
facts. The new envelope does not yet report lock-screen state or logout-inhibitor
details. Other desktops must add such capabilities before claiming those semantics;
Core must not infer them from unit state. The existing Omarchy/Plasma normal-stop
adapters remain the implementation basis, including the scoped PAM logout path.

## Display ABI 1

A query returns `session_generation`, `generation`, `outputs`, `limits` and
`settings_may_persist`. Both generations are opaque. Output and mode IDs are
opaque and valid only with their associated snapshot/session. The current Guest
maps its configuration observation to a digest; this rejects a change observed
between query and apply, but is not an atomic compositor transaction or proof
against an unobserved change-and-revert race. `limits.atomic_layout` is false.

Each output contains `id`, `enabled`, `transform`, `physical_size:{width,height}`,
`logical_position:{x,y}`, `scale:{numerator,denominator}` and `modes`. Mode fields
are `id`, physical `width/height` and integer `refresh_millihz`. Physical pixels,
logical coordinates, Windows DPI preference and application font/IME settings
are different concepts. Never reinterpret logical dimensions as physical modes.

The current adapters expose one active unrotated output, with scale in [0.5,8]
subject to integral logical dimensions. They advertise these limits and support
only `persistence:"backend-default"`. KWin may persist settings through KScreen;
no temporary-setting or automatic rollback promise is made. The collection is
extensible, but the Alpha Core fitter explicitly rejects multiple active outputs.

An apply request contains `instance`, `session_generation`, `expected_generation`,
`output_id`, `mode_id`, rational `scale`, `transform:"normal"` and `persistence`.
Unadvertised modes, stale generations and unsupported persistence/scale fail
before application. The response contains the actual snapshot and `applied:true`
only after size/scale readback. A failure may leave changed settings; callers
must re-query instead of pretending an automatic rollback occurred. Core also
rechecks the Guest and Windows window after resizing the renderer.

## Input, permissions and future desktop coverage

The current input data path remains the verified session-owned bridge. This
control API does not add keyboard injection, IME, clipboard, remote-input consent,
relative capture or universal portal access. Future extensions must advertise
them independently, bind events to session generations, define coordinate spaces
and release held keys/buttons on focus or lifetime loss. Guest owns keyboard
layout, compose/IME, user bus, PAM, seat policy, Polkit and compositor integration.
A portal backend's consent/session rules cannot be bypassed by treating it as the
existing device bridge. No X11 unrestricted-access policy is introduced.

GNOME/Mutter, Plasma/KWin, Xfce with alternative compositors, Cinnamon/Muffin,
COSMIC/Smithay and Hyprland require different Guest adapters. Desktop, compositor,
distribution and Wayland/X11 are distinct identities. Multi-session enumeration,
HDR/VRR, rotation, atomic layouts, explicit persistence, lock/inhibitor reporting
and alternate input transports remain future negotiated capabilities. None is
advertised as working by this Alpha. A compatible control API does not port a
compositor to WSX's private graphics consumer contract.

The research rationale lives in wsld `docs/DESKTOP-PROTOCOL-RESEARCH.md`; it is
engineering documentation, not a build/runtime dependency on another checkout.

## Release pairing and independent updates

`manifest.json.desktop_compatibility` binds the Guest profile digest and exact
Host runtime receipt digest, control/lifecycle/display versions, required
capabilities, opaque producer ABI 1/consumer ABI 2 and `guest-stop-v1`. The image
must state `minimum_wsx_core_version` at least `0.2.1`. Core version 0.2.1 is the
local implementation version, not evidence of a published stable Core release.
The initial Core requires all seven capabilities listed above.

All new Omarchy and CachyOS builds must package this protocol. Staging generates
the Guest profile from actual component manifests; offline validation checks those
hashes and executes the packaged `capabilities` endpoint in chroot without starting
a desktop. Finalizers always emit `desktop_compatibility` and a non-null minimum
Core version. There is no legacy-output switch.

`components/desktop-runtime` holds the checked protocol/receipt snapshot for the
Windows pairing. CI validates this metadata without a sibling checkout or Windows
binary dependency. Core separately verifies actual runtime bytes at startup.
Optional `--desktop-runtime-receipt PATH --minimum-core-version VERSION` arguments
can additionally verify local bundle bytes, but must match the checked pin and be
supplied together. Neither pin verification nor chroot capabilities establish GPU
or normal-retirement acceptance. Hardware stages remain `not_run` after CI.

Changing an image tag alone does not require a new Core. Compatible Guest
implementation changes stay behind this interface. The immutable release and
import receipt bind their actual component/profile bytes. In-place changes to
private Mesa/Venus/KWin or their locks invalidate that admission; this work does
not implement authenticated in-place replacement of the import metadata.
Unknown required protocols or graphics pairings reject explicitly.

Core still pins known Native binaries and kernel/graphics contracts. Adding an
unknown Host bundle requires a Core trust update until component distribution
and trust admission are implemented. Thus this is control-plane decoupling, not
a promise that arbitrary Core, rootfs and graphics packages can be mixed.

## Evidence boundary

Local conformance tests exercise JSON transport, capability/version rejection,
stale display generations, physical/logical conversion, readback failures,
profile mismatch and session-vs-GPU retirement. Staging and license boundary tests
run against fixtures. They are not desktop or GPU acceptance. Existing Omarchy
and CachyOS machine evidence predates this envelope; the new protocol pair still
requires a new image's start/display/input/normal stop/restart acceptance before
publication. Do not modify a running image or promote a release on this evidence.

## Protocol-only rebuild policy, 2026-11-05

The user retired old rootfs compatibility as a product target. Newly rebuilt
images use this protocol exclusively and receive fresh immutable version IDs.
No existing release attachment, WSL registration, disk or historical test evidence
is deleted or rewritten by this policy. Existing legacy code/evidence in Core is
not a reason to create another legacy image or delay the new protocol rebuild.
