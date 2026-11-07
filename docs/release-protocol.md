# Release protocol version 1

Tags are `<distribution_id>-<major>.<minor>.<patch>-r<revision>`. Recognize the
full registered distribution ID first; never split an arbitrary ID on hyphens.
Omarchy ordering is numeric `(major, minor, patch, revision)`. For the explicitly
authorized first CachyOS Draft only, `2026.11.1-r1` is an internal WSX build-date
snapshot, not an official CachyOS release. Its manifest `upstream_release` holds
the explicit snapshot label and `upstream_commit` identifies the pinned official
installer configuration; rolling package repositories are separately recorded.
Future snapshot naming, ordering and automated trigger cadence remain undecided.

Every image carries manifest.json, SHA256SUMS, sources.json, validation.json and
the named .rootfs.tar.zst archive. A completion.json marker is uploaded last,
only after every payload asset has been downloaded and its size/hash verified.
The marker lists each payload asset's hash and size and the canonical input
identity. Its existence alone is insufficient: consumers must validate the
listed bytes. Incomplete Drafts are retryable; conflicting existing asset bytes
require a new revision. Public assets are never replaced. A public release is
not writable even during retry. External promotion must be separately authorized.

Archive checks are scoped per distribution, recipe inputs and tar/zstd versions.
The first build without a matching completed release performs a full extraction
and file/metadata comparison. A later identical recipe may use stream verification
only when the prior full result, its release metadata, asset hashes and source
record are verified. Changed or unavailable evidence falls back to full. Every
build checks the compressed stream and archive hash; sources.json records the
actual verification mode and, when applicable, the referenced prior release.
Stream-only verification does not establish the new image's extracted metadata;
rolling package changes can alter that metadata even when recipe inputs match.

Build identity hashes canonical sorted JSON with distribution, upstream release
and commit, architecture, recipe revision and all critical component inputs.
Build commit records the source used but is not a substitute for component pins.
The identity and immutable version slot must agree. Serialize publication by
distribution/version/revision; never mark failed builds as completed.

## Manifest fields

- schema_version: integer protocol version, currently 1.
- distribution_id: registered distro, not a human display label.
- image_version, upstream_release, wsx_revision: matching version components.
- upstream_commit and build_commit: full 40-character Git commits.
- architecture: x86_64 initially; archive_format: tar.zst.
- cpu_requirements: when present, a mandatory CPU compatibility condition;
  `x86-64-v3` must be checked by core and cannot be treated as generic x86-64.
- asset_name: exact derived archive name; sha256: lowercase archive digest.
- compressed_size and unpacked_size: measured bytes, not package estimates.
- installation_space_required: conservative total free-space requirement including
  archive, extraction and import working space; not a guarantee against host quota.
- build_identity: digest of canonical build inputs, distinct from archive hash.
- guest_interface_abi: positive integer or null if unresolved.
- graphics_components: names, versions and hashes of complete selected input sets.
- kernel_requirements: paired protocol/kernel compatibility requirements. Core
  selects modules by actual kernel compatibility; rootfs does not ship local .ko.
- minimum_wsx_core_version: stable semantic version or null if not established.
- validation: separate build, offline, wsl_boot, gpu_first_frame, desktop and
  stability results; each is passed, failed or not_run. Candidate publication
  requires build/offline passed. Unknown compatibility never permits installation.

`scripts/contract.py` is a resolution example, not the wsld.exe implementation.
It receives already fetched and asset-verified manifests. It excludes Drafts and
prereleases, checks the tag against the manifest, filters by distro, refuses
unknown compatibility and requires real boot/first-frame/desktop acceptance.
The caller supplies actual compatibility checks. Explicit versions never fall
back. Latest does not use repository-wide releases/latest or upload timestamps.

## Candidate testing and preservation

Use `gh release download TAG --repo WSLd-wsx/wsx-rootfs --dir NEW_DIRECTORY`
with an authenticated account that can access Drafts, then verify SHA256SUMS and
completion metadata. Draft assets are not promised to anonymous clients. Core
must decompress zstd before WSL import and retain tar metadata. Candidate releases and their exact validation results are recorded separately;
these protocol instructions do not establish hardware acceptance.

Keep logs for failed attempts. No automatic Release/Draft deletion is configured.
Actions artifact retention may be bounded separately once build diagnostics are
implemented. CI success is not WSL/GPU or long-term stability evidence.

## Automatic and explicit revisions

A dispatch revision of 0 uses `distros/omarchy/revisions.json`: reviewed fixes
can advance the current upstream release without rebuilding an obsolete r1 on
every scheduled check. Unlisted new upstream versions begin at r1. An explicit
positive revision overrides the mapping but cannot replace an existing version
with different inputs. The selected revision is part of the build identity;
unrelated mapping entries are not hashed as image inputs.

For a partially uploaded Draft, recovery must validate the original build/run
identity, the source commit, each uploaded byte and the expected asset set.
Operational workflows and recovery entry points live in `wsx-rootfs-ops`.
Legacy rootfs-repository runs retain their original provenance rules. New
operations runs bind the separate operations repository and commit in the build
identity. An absent or incomplete original payload is not reconstructed by
silently rebuilding; choose a new revision when the original bytes cannot be
verified. No recovery or publication runs automatically.
