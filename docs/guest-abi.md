# Guest lifecycle CLI ABI 1

Rootfs owns user-space sessions; Core owns kernel/module selection and Windows
lifecycle. This CLI is integrated in the existing Omarchy and CachyOS product
paths. See the versioned [Guest control protocol](guest-control-protocol.md) for
the new Host/Guest boundary and its separate, not-yet-live acceptance scope.
Historical manifests with a null minimum remain legacy cases; new declarations
must state their actual minimum Core version. No evidence is retroactively added
to old releases.

Run `wsx-guest initialize --user NAME --timezone AREA/CITY` as root through WSL's
control channel. It prompts for a new password without echo. Automation may use
`--password-stdin` over an authenticated local control pipe; never use a password
argument or log the pipe. Initialization supports C.UTF-8 and UTF-8 locales provided by the installed
glibc locale data, generating the selected locale before user creation. It creates an ordinary wheel user with normal sudo/Polkit authentication.
No default password or passwordless sudo policy exists. Initialization sets the
WSL default user and session locale without restarting WSL. An optional
`pulse_server` prepare field may name an existing `unix:` socket discovered by
core; no host audio endpoint is baked into the image. Initialization is serialized. Partial initialization is not marked complete;
a retry may resume only the same recorded username/settings and matching created
UID, never take over an unrelated existing account. A crash before UID ownership
is recorded requires diagnosis rather than guessing ownership.

After wsx-core verifies and loads kernel-compatible modules, binds the actual
instance and negotiates sharing support, call `wsx-guest prepare` as root with
JSON on stdin:

```json
{
  "guest_interface_abi": 1,
  "instance_id": "REPLACE_WITH_ACTUAL_HOST_INSTANCE_UUID",
  "drm_node": "/dev/dri/REPLACE_WITH_DISCOVERED_CARD",
  "input_port": 12345,
  "sharing_path": "opaque-v1"
}
```

The example port is illustrative, never a default. The instance is checked
against the DRM device's VMBus ancestry. linear-v1 and opaque-v1 are explicit
negotiated paths; the private native contract checks remain authoritative.
The root-owned descriptor is exclusively created under /run/wsx, mode 0600.
A retained descriptor cannot be replaced by prepare. No module is loaded by
prepare and no GPU-completion claim is made.

Use `wsx-guest start --instance UUID` to keep the owning caller attached to its
systemd unit. The adapted prototype opens the real PAM session and uses the
user bus, private graphics manifests and instance-owned input receiver. Use
`status`, `stop`, or `diagnostics` with the same instance. Stop terminates only
that session unit; wsx-core must still perform real native/GPU/resource retirement.
A stopped unit alone never proves safe module unload or device removal.

The private session entry is extracted from the hash-recorded prototype. The
adapter changes only user/profile lookup, session-helper installation timing,
explicit sharing-path selection, and selection of the pinned compositor for both
sharing paths. Bundle hashes are checked before either path starts; choosing the
private executable does not enable opaque protocol flags on LINEAR. The historical module/bootstrap entry is
not shipped as the executable lifecycle endpoint. No hardware IDs, port, native
instance, Windows path or DRM card is baked into the product configuration.

Real WSL initialization, password authentication, session/menu launch, audio,
first GPU frame, sharing paths, stop/restart and sustained stability remain
unverified for the newly built image. Preserve failed instances and diagnostics.

The WSL first-run adapter retains GNOME appearance, primary paste, the real
Fcitx5 user service and the upstream welcome notification. It does not invoke
bare-metal fingerprint/Voxtype/agent setup hooks or speaker hardware tuning.
The original fixed-release first-run script remains under /usr/share/wsx/upstream
for provenance. Browser link routing, Chromium defaults and Foot terminal
selection are installed explicitly, without removing desktop applications.

## CachyOS Plasma compatibility

The initial historical private KWin binary advertises the x86-64-v3 ISA level.
The CachyOS manifest must carry `cpu_requirements.architecture_level` and core
must reject unsupported CPUs before installation or startup. The Guest repeats
this admission against the exposed CPU flags before session setup. It also
rejects KWin, Plasma Workspace or Qt base package versions differing from the
root-owned build-time compatibility lock;
rolling upgrades can therefore require an updated, paired WSX runtime. The
private KWin is used for both sharing paths, with opaque behavior enabled only
when explicitly negotiated and both actual Guest kernel ABI queries succeed.
The session owner receives SIGTERM before input/seat retirement and requests
normal Plasma logout. Full native device teardown is
not established by that acknowledgement.

The CachyOS adapter enables linger only for the initialized desktop account, so
its user manager and runtime directory survive between PAM sessions. Session
start verifies that policy. The policy persists after logout; normal account
administration can disable it, but WSX startup then fails until it is restored.
The private KWin Xwayland helper is linked to the installed Plasma helper and
the installed Plasma package versions remain locked at admission.

For CachyOS, the session unit uses process-only termination so a failed logout
does not automatically kill its seat and input children. A failed unit or retained
seat socket blocks another start; no automatic stale-socket removal or failed-unit
reset is provided. A root-owned, exclusively created instance record retains
the owner, launcher, seat and input process IDs and Linux process start times.
It is removed only after a successful launcher exit, compositor retirement and
ordered input/seat shutdown; a retained or incomplete record blocks restart.
Diagnose the actual compositor, input and seat owners and native retirement
before any manual recovery. A live compositor can prove its
instance through its executable and process environment if its transient unit
configuration has disappeared. This does not prove native GPU retirement.
