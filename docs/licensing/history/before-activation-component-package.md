# Private components built from source

The active Omarchy route compiles pinned source archives in the isolated builder.
It no longer pulls a historical WSX binary package. The previous package lock is
retained byte-for-byte at `docs/licensing/history/component-package.json` solely
as audit evidence; executable build paths do not read it. No remote asset was
deleted. The old importer and import workflow fail explicitly and have no package
read/write permissions.

## Active route

1. `distros/omarchy/build-components.sh` installs signed build dependencies and
   records actual package versions and repository configuration.
2. `scripts/fetch-components.py` downloads the archives in components/sources.json
   and validates all hashes, including cached archives.
3. `scripts/build-components.py` validates every archive again, adapts builders
   in a disposable copy, and compiles Mesa, Venus, Aquamarine and Hyprland.
   The vendored source bytes stay unchanged. The existing patch order and
   capability checks remain; CPU/GPU staging and Chromium modifier candidates
   are not enabled. CMake install search paths are disabled for relocation.
4. `scripts/assemble-source-components.py` checks successful receipts, compiled
   output hashes, source pins, flags and file confinement. It rejects escaping
   links, conflicting outputs and ELF RPATH/RUNPATH. It assembles the private
   runtime with a declared consumer ABI 2 manifest, not a hardware acceptance
   assertion. Offline rootfs dependency checks still run in the image environment.
5. Finalization records `component-source.json` and an input-derived component
   identity instead of historical archive hashes or historical desktop evidence.

The default Omarchy revision is now 2 and the known 4.0.6 mapping is r8. Changed
inputs cannot reuse an existing version slot; the existing deduplication and
immutable-public-release checks remain. No remote run, commit or publication was
performed for this migration.

## Evidence and publication boundary

The source receipt records archive URLs/hashes, recipe file hashes, actual
invocations, adapted builder hashes, output hashes and failure text. Component
receipts retain compiler commands and results. The builder records package
versions; these are rolling signed repositories, not byte-reproducible toolchains.
Source archives, adapted builders and receipts are retained by Actions artifacts
for up to 90 days after a future run. This is temporary diagnostic retention,
not a permanent corresponding-source service or a complete legal source bundle.
Generated sources and compiler trees remain in the build workspace; automatic
pruning is disabled pending verified durable archival. Not all generated inputs
are transferred by the diagnostic artifact steps.

`hardware_validation` remains `not_run`, `license_review` remains `pending`, and
`corresponding_source_complete` remains false. The source path does not make the
whole image compliant by construction. Full dependency/source closure, notices,
generated input retention and hardware acceptance remain separate work.

The rootfs payload transfer, Draft publication job and publication retry workflow
now invoke the existing review tool's `--require-release-ready` gate, which
intentionally fails while the licensing review is unresolved. No change to the
contract-level publisher's asset verification, version resolution, Draft isolation
or immutable-public handling is made. Direct use of that low-level publisher
remains outside the new workflow gate; no such invocation is authorized here.
Debug workflows still cannot upload candidate payloads or publish Drafts.

## Paired source packages and CachyOS

The component workflow accepts `omarchy` or `cachyos-plasma`. Each package includes
its matching Mesa/Venus producers and desktop consumer. CachyOS builds the pinned
KWin 6.8.1 archive with the vendored DRM/opaque adapter; the separate experimental
virtual-output KWin implementation is not used. The signed Arch 2026-10-28
snapshot supplies dependencies, with explicit KWin/Plasma/Qt ABI checks and exact
installed versions recorded. Configure, compile and install logs are retained.
No local deployment or historical runtime binary is a build input.

`package-source-components.py` creates a profile-specific tar.zst, manifest and
SHA256SUMS. `consume-source-components.py` requires an externally supplied archive
SHA-256 and matching profile, rejects unsafe archive entries and verifies the
entire extracted file set against the source receipt. It refuses existing output
directories. The CachyOS workflow builds this package, consumes it through that
same admission path, then configures and validates the rootfs. Component packages
are Actions artifacts, not public Releases or OCI replacements at the old URL.
Standalone reuse must pin the selected artifact digest; never resolve by latest.

The old import command remains retired. Rootfs payload transfer and Draft
publication retain the existing publication review gate. This implementation
restores source recipe availability, not hardware acceptance or license clearance.
The private install prefix remains `/opt/wsx/kwin-opaque-6.8.1`; the session uses
the staged runtime and version-checked Xwayland helper compatibility link.

## Local validation scope

Fixture tests cover source-hash rejection before compilation, failed receipts,
post-build corruption, escaping links, conflicting merges, unchanged safety flags,
portable builder adaptation, runtime manifests, retired import refusal and the
CachyOS pre-network failure. Full compilation, source URL availability, patch
application to real archives and WSL/GPU acceptance have not been verified in this
turn. Use the dedicated source workflow only after separately authorizing remote
execution; a successful fixture test is not a successful compiler run.

## Implementation verification (2026-11-03)

The pinned local KWin archive passed hash verification and real opaque patch
application with fuzz disabled. Twelve source-route tests, seven real zstd archive
round-trip/admission tests and ten Plasma staging tests passed. YAML and Python
syntax checks passed. Tests use fixture runtime bytes, not compiled KWin outputs.
The current execution environment has no Docker or Arch compiler sysroot; a full
Actions compile, ELF dependency check and real desktop acceptance remain not_run.
No remote dispatch or publication occurred during this change.


## Post-merge license review

See licensing/RECHECK.md. The new component binary uploads now also require the
current license readiness gate before transfer. This does not make compilation,
packaging or temporary source artifacts proof of complete license compliance.
