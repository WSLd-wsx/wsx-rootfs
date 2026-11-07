# Independently compatible Host updates

The release's runtime_receipt_sha256 remains the immutable tested baseline,
not a claim that every later Host is incompatible. A newer Core may carry a
reviewed, directed replacement edge from that exact baseline to an exact new
runtime closure, scoped to the exact Guest profile. This requires no change to
published image bytes or Guest control protocol. Older Core retains exact-pair
behavior. A component receipt cannot authorize its own replacement.

Host-only view management, diagnostics and presentation changes may qualify
when they preserve Guest control major/minor requirements, producer/consumer
ABIs, opaque sharing layout, wire commands, kernel-module bytes, resource
identities and retirement guarantees. Version numbers alone are insufficient.
Input changes additionally require focus/isolation regression evidence. Changes
to kernel modules, Guest allocation/layout rules, Venus commands, required Guest
capabilities or ownership require a new separately reviewed pairing; they are
never automatically admitted by this policy.

The corrected view-v1 candidate changes wsx-native-host.exe,
libvirglrenderer-1.dll and wsx-input-host.exe relative to baseline 617965791e69.
The first two-file candidate was withdrawn after real input acceptance failed. All other receipt
entries are identical. Core's checked host-updates.json specifies the full
replacement digest and exact profiles. Selection is explicit during acceptance;
it is not a default upgrade or proof of successful GPU testing. Guest profile,
archive/import provenance and full component byte verification remain mandatory.
Unknown profiles, arbitrary replacement hashes, reverse/downgrade edges and
legacy images are rejected. Updates do not replace a running Owner in place.
Rollback requires normal retirement and explicit selection of an admitted
baseline, not reassignment of live GPU resources.

Evidence distinguishes declaration admission, full byte verification, actual
Guest preflight, desktop/input continuity, view detach/reattach and normal stop.
A rootfs need only be rebuilt when its Guest implementation or required contract
changes; a Host-only update is distributed as a new immutable component closure.

## Concurrent distro device selection

PCI Owner configuration ABI 2 alone is insufficient for simultaneous desktops.
The additive `graphics.distro-device-view-v1` Guest capability means startup
prepares an exact-instance distro-local DRM mount view before launching any
compositor or app. Both primary and render nodes must belong to the same
validated VMBus Owner; global first-device enumeration must not cross desktops.
All participating distro sessions need this capability before startup. Existing
published Omarchy r12 and CachyOS r1 images need new immutable revisions for this
behavior; locally deployed overlays are diagnostic evidence, not new releases.

Live testing observed global render-node selection and a peer compositor taking
DRM master on a newly hotplugged device. The local view fixed render selection;
Omarchy restarted successfully with its view. Concurrent first-frame/input and
independent retirement acceptance is still incomplete. A failed Plasma logout
also exposed lingering instance-tagged D-Bus services. The Guest retirement
adapter now normally stops only wholly owned user service/scope units, preserving
the user manager and refusing units shared with another session. Residual service
drain passed in the test Guest; an already quarantined Native Owner remains a
separate unresolved Host lifetime and cannot be declared retired by this change.

## Per-distro input view

Real concurrent testing found both Guest compositors could receive the same
keyboard input because their shared-kernel evdev nodes were globally visible.
The input producer now labels each uinput device with its Host instance UUID;
Guest startup creates a distro-local /dev/input view with exactly its keyboard,
pointer and wheel nodes. The additive graphics.distro-input-view-v1 capability
is required together with graphics.distro-device-view-v1 for ABI 2 startup.
This is a cooperative device selection boundary, not isolation from Guest root.
Instance-labelled device selection and actual temporary uinput/mount tests passed;
Omarchy's real single desktop accepted keyboard and mouse. Both fixed desktop
sessions and cross-window focus isolation have not yet been accepted together.

An early session failed before its compositor was started. Exact owned input
cleanup and session-drain tests led to separate reporting of failed-but-drained
session state, with GPU retirement still explicitly false. New source changes
require new immutable rootfs revisions; current image tests use logged overlays.


## Input-view live acceptance on the RTX test host

With logged Guest test overlays applied, Omarchy and CachyOS both reached their
Windows desktop windows concurrently. Actual /dev/input mounts exposed exactly
three instance-labelled nodes per distro with distinct device minors. The user
confirmed mouse, keyboard, menus and ordinary input on both desktops and that
input in one terminal did not appear in the other. Each viewport detached and
reattached to its original Host. Both directions of normal independent stop and
restart passed with the peer Host kept running, followed by user confirmation of
both desktops and input isolation. This validates the test overlays on this one
RTX machine; it is not acceptance of rebuilt rootfs images or other GPUs.

The next image revisions declare both isolation capabilities as required and
pin Host receipt `442f6032d8645c413b7398e2654c669169e79e9b46e79220134bb881b51d0561`.
Capability admission is required even where Core versions share the same
nominal version number. This Host closure is currently available in the test
machine's verified local cache; publishing a generally available runtime remains
separate work. Building these images does not establish desktop acceptance.
