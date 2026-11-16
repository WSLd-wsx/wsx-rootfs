# Approved component ownership

The reference sources are recorded in [provenance.json](provenance.json).
Historical private build evidence is retained. The new source-only route is
locally tested but has not run on Actions; it does not inherit historical acceptance.
Cross-repository lifecycle compatibility and hardware acceptance remain pending.

| Component | Owner | Admission requirement |
| --- | --- | --- |
| Private Mesa/Zink/Venus and GBM adapter | rootfs | Pin Mesa/Zink 26.1.8 and Venus 26.2.4 plus reviewed patch closure and build inputs; retain runtime negotiation |
| Hyprland and private consumer integration | rootfs | Pin the Hyprland/Aquamarine source commits and reviewed consumer patch closure in components/sources.json |
| KWin private consumer | rootfs CachyOS recipe | Include display-destruction and opaque RMFB fixes; separate acceptance |
| Guest kernel modules | wsx-core distribution/selection | Match actual WSL kernel, symbol CRCs and paired transport ABI; reject known-bad allocation-base layouts |
| Independent Windows Venus/Rutabaga host | wsx-core | Pair native contract versions with Guest; stock WslService manages VM |
| Session and network adapters | rootfs | Versioned Guest interface, real PAM/user bus and injected instance identity |

The user approved this ownership split on 2026-10-31. No minimum wsx-core version
or public Guest lifecycle ABI has been established. These values must remain
unknown until an actual cross-repository contract exists. Existing producer ABI
1 / consumer ABI 2 is not by itself a public lifecycle ABI specification.

## Evidence distinctions

- Reference HEAD is not the complete verified network source: the v4.0.6 profile
  is untracked and the installer/README have working-tree changes. The vendored
  network adapter preserves those exact bytes and its strict hash admission.
- `omarchy-406-start-01/result.json` records v4.0.6 visible desktop, shell ping
  and successful menu IPC. This is bounded startup evidence, not CI validation.
- The private source lock names Mesa 26.1.8, virglrenderer 1.3.0 and Rutabaga
  0.1.85. Windows host renderer/Rutabaga delivery belongs to wsx-core; the
  selected Guest patch closure is vendored and checked by content hash.
- Opaque kernel build 05 restores embedded DRM bases to allocation start.
  Never package module SHA-256
  `70d83be693bc714378b41f22ff38f2a1d459b363b853be214114c5988600def0`.
- Chromium shared-format admission remains application-scoped. Its paired
  modifier/format fix has bounded Iris Xe WebGL and lock/unlock evidence;
  earlier modifier-only and layout-cache trials failed. Do not globally enable.
- Existing Mesa builders depend on local artifact/sysroot directories. They
  are adapted only in a disposable copy by scripts/build-components.py, with
  pinned archives and an isolated signed-package build environment.
- The fixed official source and WSL reference have been reviewed. The recipe
  installs desktop packages/configuration without running the bare-metal
  installer or Limine migration; see omarchy-wsl-reference.md.

## Implemented candidate first-boot contract

Prepare a locked root account and no reusable user password. An authenticated
wsx-core initialization operation supplies username, locale and timezone; set
password through a non-logged protected input channel. Establish normal PAM,
sudo and Polkit authentication, then mark initialization complete atomically.
Do not start a desktop before initialization and compatibility admission.
Runtime device/instance/display parameters are discovered or injected, never
persisted from a development host into an image.

## Portable builder extraction

The vendored reference builders and patches remain byte-identical to provenance
hashes. `scripts/build-components.py` changes the disposable Mesa builder's
source lock/archive lookup and pins Hyprland's Glaze dependency, retaining
prerequisite checks, patch order, private
prefix and source-change audit. It enables neither staging nor the Chromium
candidate nor the failed layout-cache experiment. The selected Venus builder
uses 26.2.4, not the older baseline Mesa source-lock version.

The Arch Linux builder is pinned by platform manifest digest. Signed rolling
package versions are recorded, but repository snapshots are not yet frozen.
Successful local historical builds needed dependency configuration repairs;
all four private components now compile on Actions as recorded in build-evidence.md.
That result does not establish a working rootfs or a real desktop.
The `components.yml` workflow is a compilation diagnostic, not a rootfs release.

The latest source inspection also confirms that Omarchy 4.0.6's official
repository is `omacom/omarchy` (the older basecamp URL redirects). Stable release
417808603 resolves to commit 237f1b4071a0bff2296c6d740ba2b9fd695ebfa0.
The extracted exact-hash network adapter applies successfully to that source.
The first Actions component build failed on Arch package names libseat/libeis;
these were corrected to seatd/libei without changing signature checks.

## CachyOS real-machine follow-up

[The r1 handoff](cachyos-r1-runtime-handoff.md) assigns image/session fixes
RF-1 through RF-3 to rootfs and actual-device authorization/input reconnect
CORE-1/CORE-2 to core. Local fixes and bounded presentation do not establish
that the unmodified Draft or reusable lifecycle interface passes acceptance.

## Image assembly versus compiled component evidence

Protocol-only rootfs rebuilds keep the original component receipt, source archive
and notices immutable. `image_materials.py` checks the actual compiled runtime
outputs, reconstruction graph, source hashes and existing license classifications
before reuse. Added image-only outputs do not imply recompiling Mesa/Venus/KWin.
Changes to compiled inputs or their terms still require a matching component build.

The current image gets a separate `image-assembly-source-snapshot` with
`compiled:false`, the original component receipt digest and current recipe hashes.
Its notices/map cover the new Guest files and are installed in the image. Original
component materials remain untouched and available through their shared source
bundle. The image recipe attachment carries the new source snapshot and map.
Neither snapshot is a license change or a claim of hardware acceptance.

The original component Actions runs returned HTTP 404 during the protocol rebuild.
For GHCR, durable admission uses the fixed OCI digest and repository/commit/run/
profile labels, exact package bytes, and the separately published hash-pinned
source index/receipt. The source-delivery origin must equal the selected registry
pin. Run availability is not a package lifetime guarantee; a missing run is never
reported as a current successful run. The Actions-artifact transport retains its
live successful-run and expiry checks.
