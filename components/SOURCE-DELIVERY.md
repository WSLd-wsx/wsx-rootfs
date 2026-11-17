# Shared graphics source delivery

> Operations update: the Omarchy rootfs workflow runs in wsx-rootfs and selects
> the digest-pinned component in `omarchy-selection.json`. Component production
> and shared-source preparation remain in the private operations repository.
> Existing published source assets are unchanged; this does not establish
> complete system-package source delivery.

The repository was recreated on 2026-11-16 and previous image and shared-source
Releases were retired. Both default component selections and public-source pins
are intentionally unset. Build and verify a new component source closure, then
publish and select a matching shared-source Release before assembling a new
image. Historical GHCR identities remain evidence, not default selections.

New compiler runs collect the three shared archives directly after runtime
assembly and emit component package schema 2. They do not create an intermediate
`sources.tar` or copy expanded upstream trees into the delivery package. Compilation
still uses the full pinned inputs in its temporary workspace. KWin original and
prepared sources, patches and build materials remain included. Existing schema-1
packages retain their original verification path; new packages verify the shared
index, archives, notices and original runtime receipt on admission.

Compatibility with existing binaries permits only the explicitly pinned old/new
hash pair for the post-build `scripts/component_materials.py` collector, plus
the exact `scripts/shared_sources.py` metadata-reader-only transition recorded
in `reuse-components.py`. Neither exception applies to inventoried compiled sources. Compiler,
ABI, installed source and license policy changes still require a new component
build. This exception does not replace verification of the old package bytes.

New rootfs payloads use `source_delivery_schema: 2`:

- `image-recipe.tar.gz`: this image's original assembly scripts, configuration,
  vendored inputs and existing license texts; individual licenses remain intact.
- `graphics-sources.json`: the exact shared source index, including fixed upstream
  origins, modifications/build material entries and source archive hashes.
- `component-source.json`: the original component build receipt, bound exactly to
  that index. The rootfs does **not** repeat the large `component-sources.tar`.

The shared source-only release contains three compressed archives and its index:

| File | Content |
| --- | --- |
| `graphics-notices.tar.gz` | All retained original component notices and license mappings |
| `graphics-changes.tar.gz` | Original/adapted build scripts, patches, generated definitions, build records and fixed source origins |
| `graphics-retained-sources.tar.gz` | KWin's original/patched source and build materials for CachyOS; fixed Mesa/Venus archives retained conservatively because their trees contain mixed licenses |

Hyprland, Aquamarine, udis86 and glaze use pinned source references plus retained
notices and modifications. Their full upstream archives and expanded trees are
not repeated in the shared projection. Unused profile inputs are omitted.
Mesa/Venus expanded trees are reconstructed by their retained original/adapted
builders and patches, so those expanded copies are omitted. Unknown material
paths are retained; new upstream archive identities require projection review.
This is a component-specific delivery policy, not a blanket license inference.

The shared release tag is derived from the profile and content. Two images that
use the same component receipt reuse exactly the same shared source index; their
small image recipes may differ. A changed component receipt requires a matching
source bundle. Existing schema-1 releases retain their assets and validation.

## Preparation and activation

Dispatch `shared-graphics-sources.yml` with the required profile and
`publish_draft=true`. It reads the pinned existing private GHCR package on an
Actions runner, verifies the original receipt, prepares the source-only archives,
creates/reuses a Draft and reads back every uploaded asset. It neither compiles
nor uploads binaries and never changes the Draft's visibility.

For an explicitly authorized manual rootfs workflow, a source-only Draft may be
published as a non-latest Pre-release after the complete asset set has been read
back and verified. Verify anonymous access before selecting its exact index. This
authorization does not promote a rootfs Draft to stable. For manual activation:

```sh
python3 scripts/select-shared-sources.py --profile omarchy \
  --tag graphics-sources-omarchy-<content-id> --sha256 <index-sha256>
python3 scripts/audit-licenses.py
```

Commit the selected pin and refreshed inventory. `components/source-delivery.json`
keeps the original private component origins separate from public source pins.
A null public pin intentionally blocks new schema-2 image builds before assembly;
it does not silently fall back to a large bundled archive or a private URL.

The source index is downloaded without credentials. Rootfs preflight and
publication check that the source release is public, every asset is uploaded,
and its GitHub-reported SHA-256 and size match. Public source artifacts must not
be deleted while referenced by images. Existing source assets are never overwritten.
The original component package is not made public by this process.

For a private rootfs repository, the operations resolver instead saves the
verified source-only materials as a private pre-release and verifies them using
authenticated access. Image candidates can then be saved separately as Drafts.
Before public distribution, verify that the same source materials are publicly
accessible under the applicable licenses; private access does not establish this.

## Upstream distribution packages

Prefer the original upstream license, notices and exact-version source route for
unmodified Omarchy, CachyOS and other distribution components. Do not add a
blanket WSX license to those works or replace their existing rights. Separately
identify WSX-owned recipes, Guest code and modifications. This approach does not
replace obligations to retain or supply corresponding source, changes, build
materials and notices when the applicable upstream terms require them.

Follow the selected distribution's package and license terms for unchanged
packages. Keep their installed name/version inventory and original notices; do
not require a separate OSI classification of every package. Use the recorded
repository/version data and upstream package-source history to find the
corresponding sources and packaging materials when required. A rolling package
page is a discovery entry, not proof that a particular version's source remains
available. Maintain access to the applicable source, modifications and build
materials alongside the binary delivery for as long as required. WSX-modified
graphics components retain their pinned source index and source release above.
Historical r19 source-access evidence is retained separately in wsx-guest-sources.

Graphics builds may run in the public source repository. Their binary destination
must be the existing verified private GHCR package; diagnostic attachments are
disabled on public repositories. Omarchy and CachyOS candidate publication is explicitly enabled with verified
public shared source references.
This does not change ABI or GPU behavior or claim complete system-package source delivery.
GPL/other upstream obligations remain separate from the original WSX PolyForm
scope. No additional restriction is imposed on upstream source archives.

## Installed package discovery and known FDK AAC source

New Omarchy and CachyOS candidates record `package_source_inventory` in
`sources.json` from the installed pacman metadata and the build's recorded
repository/version list. Each row retains the package/base/version, declared
licenses, hashes of the installed package metadata and discovery URLs. These
URLs are not verified exact source archives; the inventory does not claim that
all packages require source delivery or that their applicable obligations have
been met.

For the specifically reviewed Arch `libfdk-aac 3.0.0-1` library and NOTICE
bytes, the finalizer attempts to collect fixed upstream and Arch packaging
archives. It checks their pinned SHA-256 values and retains successful downloads
inside `image-recipe.tar.gz`, with a source manifest bound to the image library
and notice hashes. A different version, different installed bytes, inaccessible
archive or changed hash leaves the source status unresolved and does not
manufacture a match. This optional collection does not assert a reproducible
build, resolve patent licensing or make a whole-image compliance claim. The
component and system-package review remains separate.
