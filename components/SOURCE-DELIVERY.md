# Shared graphics source delivery

Existing private GHCR packages remain unchanged and readable. No recompilation
is needed to project their historical source evidence.

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

After separate approval to publish that specific source-only release, publish it
as a non-latest Pre-release. Activate the exact resulting index using:

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

Graphics builds may run in the public source repository. Their binary destination
must be the existing verified private GHCR package; diagnostic attachments are
disabled on public repositories. Omarchy and CachyOS candidate publication is explicitly enabled with verified
public shared source references.
This does not change ABI or GPU behavior or claim complete system-package source delivery.
GPL/other upstream obligations remain separate from the original WSX PolyForm
scope. No additional restriction is imposed on upstream source archives.
