# WSX rootfs agent guide

## Collaborative workspace scope (2026-11-05)

The user authorizes coordinated local changes in all four sibling repositories
under the `/mnt/wsl/u/wsx` workspace: `wsld`, `wsx-rootfs`, `wsx-pro`,
`wsx-proto` and `wsx-rootfs-ops`. This supersedes earlier read-only or narrower repository-edit scope
in this session. Before changing a repository, follow its own `AGENTS.md` and
any applicable nested instructions. Keep repository responsibilities, license
boundaries, independent builds and existing unrelated changes intact. Reuse and
trace verified prototype work; this authorization does not make the prototype
a product runtime dependency. Do not create a workspace-level `AGENTS.md`.

This expands local editing scope only. It grants no new authorization for
commits, pushes, publication, remote workflows, license changes, destructive
operations or disruption of existing desktops/services. Existing explicit
authorizations retain their original scope.

## Scope and architecture

Own the independently runnable desktop rootfs recipes, source inputs, image
validation and release protocol for `wsx-omarchy` and `wsx-cachyos-plasma`.
Keep automated workflow definitions in the private sibling `wsx-rootfs-ops`;
`components/workflow-history/` contains non-running historical evidence only.
Retain locally usable build and verification scripts and component source materials.
Historical workflows, build receipts and their license grants remain valid.
Unsupported entries must fail explicitly, never report successful support.

wsx-core owns download, verification, decompression, WSL import, instances,
Windows GPU hosting, input/presentation connections and lifecycle. Guest
components expose versioned prepare/start/status/stop/diagnostics interfaces.
This repository defines the release protocol, not the real wsld.exe client.

## Reuse and graphics safety

Before implementation inspect wsx-proto instructions and relevant guest-compat,
guest-opaque, network, session and device-host/production sources and evidence.
Record source paths, commits AND working-tree content hashes, upstream versions
and exact validation scope. Distinguish verified behavior, candidates, simulated
checks, failures and defective versions. Prototype changes are permitted under
the collaborative scope above; preserve evidence and do not disturb running
desktops. Vendor reusable code with provenance or pin a
CI-accessible dependency; CI must not depend on local workspaces or deployments.

Use the independent Venus/Rutabaga Windows host with stock WslService. Preserve
capability negotiation, exact allocation/layout contracts, resource identity,
generations, synchronization and retirement. Never require universal LINEAR,
represent opaque images as DRM modifiers, weaken checks or fabricate completion.
Never implicitly enable CPU/GPU staging, restart WSL/services or package the
known-bad virtio-gpu module with embedded DRM bases away from allocation start.
Preserve hardware-specific evidence without claiming universal compatibility.
Do not globally enable Chromium modifier candidates without scoped acceptance.
Private Mesa/Venus, compositor patches and kernel modules require a paired
compatibility contract; distribution packages are not interchangeable substitutes.

## Build and release

Detect official stable upstream Releases every six hours by default; exclude
Draft, prerelease, alpha, beta and RC releases. Pin the release commit; a tag or
branch tip alone is not stable-release evidence. Support manual version, retry
and revision selection. Deduplicate by distro, upstream commit/version,
architecture, recipe revision and key component inputs, including complete
Drafts and public releases. Failed or partial uploads are never completed builds.
Serialize publication for an identity and safely retry incomplete candidates.
Changed inputs require a new WSX revision; public assets are immutable.

Publish only Draft releases after basic checks, with .rootfs.tar.zst, SHA-256,
versioned machine-readable manifest, sources/components and validation reports.
Verify every required uploaded asset before recording completion. Never promote
a Draft without explicit separate authorization. Measure compression ratio,
time and peak memory before choosing resource limits. Perform full extraction
and metadata verification on the first build of a recipe and whenever its
inputs or archive tools change. Reuse only verified, completed prior evidence
for the identical distribution, recipe and tool versions; otherwise fail safe
to full verification. Every build still checks the compressed stream and hashes.
Report skipped full comparisons honestly; they do not establish the current
image's extracted ownership, links, ACLs, xattrs or capabilities.

Client resolution recognizes a valid distro ID before parsing a version. Latest
means the highest explicitly ordered compatible complete public stable image
for that distro, never repository-wide releases/latest or upload time. Explicit
versions fail if missing/incomplete/incompatible; never silently fall back.
Drafts and prereleases are excluded from both normal install forms. wsx-core
verifies and decompresses zstd before WSL import. Draft testing uses authenticated
gh downloads. Unknown minimum core/ABI compatibility must remain explicitly
unresolved and cannot be invented.

## Image hygiene and evidence

Include shared systemd/PAM/user D-Bus/Polkit, Wayland/Xwayland, application launch,
terminal/fonts/audio and WSL network foundations. First boot initializes user,
password, locale and timezone; authentication must work without universal
passwords or bypass policies. Never log passwords or include them in manifests.
Exclude credentials, personal data, SSH host keys, machine identity, caches,
build mounts and contents of proc/sys/dev/run. Do not bake GPU IDs, UUIDs/LUIDs,
PCI/DRM nodes, instance IDs, ports or Windows deployment paths into the image.

Record signed package sources/versions, patches/hashes, toolchains and recipe
inputs. Traceability does not imply byte reproducibility with rolling repos.
Validate structure, dependencies, links, metadata, hygiene, archive extraction,
schema/hash/assets, deduplication, retries and version/Draft isolation.
Separate build, offline checks, WSL boot, GPU first frame, desktop functionality
and sustained stability. Never substitute container checks for hardware evidence.
Preserve failure evidence and historical releases; do not bulk-delete candidates
or public versions. Keep operational details and provenance in linked docs as
those documents are created; never turn transient machine state into defaults.

## Remote execution and authorization

Check actual remote, branch, gh authentication and permissions. Use gh to push
through the real Actions loop: identify the exact commit run, watch it, inspect
failed logs/artifacts, fix and rerun until a complete downloadable Draft exists.
Normal commits, pushes, dispatches/retries and Draft creation/completion are
already authorized. No force pushes, history rewrites, public promotion, remote
release deletion, unrelated messages or changes to other repositories are
allowed. Use least privilege; grant release write only where necessary and pin
third-party Actions to reviewed commits. Keep signature verification enabled.
Report concrete external blockers and the minimum needed intervention rather
than claim remote success or loop on deterministic errors.

## Pending decisions

Approved ownership: rootfs preinstalls the pinned private user-space graphics
stack, compositor and Guest session adapters. wsx-core supplies the Windows host
and selects, verifies and loads modules for the actual WSL kernel. Versioned
compatibility manifests must reject mismatched combinations. Public lifecycle
ABI and minimum compatible core version still need implementation/verification.
Do not publish an incomplete image as bootable.
CachyOS rolling snapshot naming and trigger cadence remain undecided. The user
authorized `2026.11.1-r1` only as an internal test Draft snapshot label; it is
not a CachyOS official release or an established long-term naming policy.
Update confirmed decisions promptly and preserve unresolved ones explicitly.

All repository prose, comments, configuration descriptions and commit messages
must be English. Communicate with the user in Chinese.

## Detailed contracts and evidence

- [Component ownership](docs/component-ownership.md) and [provenance](docs/provenance.json).
- [Release protocol](docs/release-protocol.md) and [manifest schema](schema/manifest-v1.schema.json).
- [Candidate Guest ABI](docs/guest-abi.md).
- [Build evidence](docs/build-evidence.md); keep hardware acceptance separate.

The user-supplied Omarchy-wsl reference is a text-only distribution. Reuse only
applicable WSL boot/network/initialization patterns; never adopt its CLI-only
profile or GUI-removal logic. WSX remains a full desktop image with the paired
private graphics stack. See [reference audit](docs/omarchy-wsl-reference.md).

Manual runner debugging uses the pinned actor-key tmate entry described in
[runner-debugging.md](docs/runner-debugging.md). Debug runs must not publish
candidate payloads or Drafts; commit interactive fixes and verify a normal run.

## Guest control protocol work in this session

The earlier Guest-only editing scope is superseded by the collaborative scope
above. Local changes may span the four repositories. This scope update does not
authorize remote build/publication or modifying running images. The source implementation is specified in
[Guest control protocol 1.0](docs/guest-control-protocol.md). Keep future desktop
research separate from actual support; only the existing Omarchy/Plasma adapters
are implemented. Never expose internal Python functions, package paths, systemd
unit names or compositor sockets as the Host contract. Unknown required versions
fail without downgrade, and session logout never substitutes for GPU retirement.

## Protocol-only image builds (2026-11-05)

The user no longer requires old rootfs compatibility. Rebuild Omarchy and CachyOS
with Guest control protocol 1.0, mandatory desktop compatibility metadata and the
checked Native runtime pairing. Use new immutable image versions, never overwrite
old assets. Verify the packaged public endpoint offline; report hardware stages
as not_run until real acceptance. This does not authorize deleting existing
registrations, VHDs, release history or evidence.

The user explicitly authorized building and publishing the new protocol candidates
`wsx-omarchy-4.0.6-r12` and `wsx-cachyos-plasma-2026.11.5-r1` as public Pre-releases
with the existing checked source-delivery workflows. This includes the necessary
normal build commits/pushes and workflow dispatches/retries. It does not authorize
stable promotion, overwriting old assets or deleting existing instances.

## Concurrent desktop device admission

Advertise graphics.distro-device-view-v1 and graphics.distro-input-view-v1 only
with the packaged exact-Owner DRM/input view helpers and startup integration. Apply the distro-local view before any
compositor/app starts; retain namespace propagation isolation and reject current
DRM clients before replacement. Every concurrently running distro needs this
behavior. This view is cooperative graphics selection, not a security boundary
against Guest root. Normal logout must drain exact-instance user service/scope
units without stopping a shared unit, another session or the user manager.
