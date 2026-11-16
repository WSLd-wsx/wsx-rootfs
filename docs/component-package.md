# Independently built graphics components

The components workflow compiles pinned Mesa/Venus plus Hyprland/Aquamarine for
Omarchy, or KWin for CachyOS Plasma. It records source hashes, recipes, compiler
results, runtime hashes, package versions and notices. Original vendor bytes and
GPU pairing checks are unchanged. Historical verified-components imports remain
retired.

Rootfs workflows do not rebuild the large graphics stack. They admit the explicit
same-repository run/GHCR digest/manifest hash in components/reuse.json, verify profile,
source policy and integrity, then stage the runtime. Missing or incompatible
packages fail. Small Guest input adapters still compile during image staging.

Source licenses are effective; see ../LICENSE-MAP.md. test_only=true produces only
source diagnostics. test_only=false permits the owner's checked private binary
artifacts with paired source materials; it does not create a Release. Public
image distribution and promotion remain unapproved. GHCR retains the binary and
paired sources together until explicitly removed; this is not a promise of permanent hosting. Hardware validation is separate.

Build from the active-license commit before selecting a reusable package. Record
the actual run/GHCR digest/source commit and manifest hash printed by the component
workflow. Rootfs source delivery retains both the original component materials
and the current image recipes. See release-protocol.md and
licensing/PRIVATE-ARTIFACTS.md for the exact gates and retained limitations.

The previous migration report is retained under
licensing/history/before-activation-component-package.md as dated evidence.

## Private registry transport

New component packages use `ghcr.io/wsld-wsx/wsx-rootfs/source-components`.
Each image is a non-executable scratch container containing the five existing
package files under `/payload`, including `sources.tar` and license materials.
Publication verifies private visibility and reads back every file before reporting
a pin. Rootfs admission requires a successful matching component workflow, immutable
image digest, matching profile/run/revision labels, manifest hash and existing
source/runtime integrity checks. Legacy artifact pins remain readable.

The component workflow needs `packages: write`; consumers need `packages: read`.
Authentication uses the job token in a temporary Docker configuration. No package
is made public. The retired `verified-components` package is not restored.
Optional Actions diagnostic uploads may warn when Artifact storage is unavailable;
the paired sources in the GHCR payload remain mandatory. Omarchy rootfs payloads use private GitHub Pre-releases after the mandatory
rootfs gate, including every required source asset. Uploads remain Draft until
all assets and the completion marker pass remote byte verification. CachyOS rootfs
transport remains unchanged. This is private storage, not public publication.

Compiler concurrency is selected from CPU affinity/cgroup quotas and available
memory, reserving 2 GiB plus 2 GiB per compiler task. Each builder reports elapsed
time. Existing vendored builders are adapted only in the disposable build copy.
A two-core runner remains CPU-limited; this change does not promise a faster first
build on the same hardware. Successful digest-pinned packages avoid recompilation
in subsequent rootfs builds. No upstream version or graphics safety option changes.
