# Publication readiness: unresolved review

This is a working technical review, not legal advice, a license grant, a complete
SBOM, or approval to distribute. The repository and the images are collections
of independently licensed material. Do not describe either as having one blanket
license. Source with a non-commercial restriction is source-available, not OSI
open source. No new WSX license or copyright holder has been selected here.

## Distribution blockers

- Establish the rightsholder, previous grants and recipients for each relevant
  version. Preserve existing MIT, GPL and Apache notices and any rights already
  granted; a Git author identity alone is not ownership evidence.
- The KWin patch changes GPL-2.0-or-later files and adds WSX source to KWin.
  Determine the actual obligations of each distributed combination. The
  CachyOS r2 historical binary and inspected source inputs are separately
  pinned; their exact correspondence and complete corresponding source remain
  unproved. Recover the build closure or build a new independently traceable
  revision. Source hashes alone are not corresponding source.
- The Apache-2.0 protocol header under `vendor/rvgpu` needs the applicable
  license copy and a review of upstream copyright, changes and NOTICE. Review
  the actual payload as well as this repository. See the authoritative
  [Apache license](https://www.apache.org/licenses/LICENSE-2.0).
- `components/package.json` identifies an interim binary, not an auditable
  source build. Record exact sources, patches, generated inputs, dependencies,
  toolchain, build and installation instructions, notices, output hashes and
  Guest/Host compatibility for any replacement. The existing component builder
  does not establish a complete KWin build or historical binary correspondence.
- Audit the actual image packages, licenses, sources, fonts, artwork, codecs and
  trademarks. Previous examination identified unrar in CachyOS r2; it cannot
  support an unqualified claim that the entire image is open source. Do not
  modify historical images or release assets to resolve this review.
- Inventory all remote refs, releases and attachments, Actions artifacts,
  package access and history before any visibility or history change. A local
  Git bundle does not include release attachments, registry content, LFS
  objects, forks or clones. No history rewrite or publication is authorized by
  this document.

## Scope and evidence

Existing `docs/provenance.json` and `components/cachyos-provenance.json` map
inspected source inputs; `components/sources.json` pins several upstream
archives. `scripts/check-provenance.py` verifies recorded vendored bytes, not
license coverage, source completeness or binary equivalence. The build scripts
and existing release protocol remain in force. Build success is not evidence of
GPU or desktop acceptance. A public prerelease needs separate approval; normal
installation must continue to reject drafts and prereleases.

The intended review categories are image recipes and Guest integration,
independent WSX graphics, upstream patches and GPL combinations, third-party
license material, and build and test tools. Placement is not a determination of
ownership or of whether a work is combined. Keep unresolved material isolated
from public distribution until reviewed. Do not replace upstream terms with a
non-commercial restriction.
