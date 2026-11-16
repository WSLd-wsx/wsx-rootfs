# Module licensing plan — review only, not effective

The owner selected module-level licensing: retain applicable upstream terms for
excluded modules and consider the same unmodified PolyForm Noncommercial 1.0.0
for independently licensable WSX modules. No new grant is activated by this plan.
The licensor designation is WGY (GitHub: wgy-wsx) <wgy@wsxdesk.com>.

Modules are logical path/build boundaries. Moving a file or using IPC does not
change its rights. Existing paths are retained to preserve provenance and build
contracts. modules.json defines machine-checkable review membership; the existing
rules.json continues to record per-file license evidence and exceptions.

| Module | Proposed treatment | Concrete boundary |
| --- | --- | --- |
| wsx-independent | PolyForm Noncommercial candidate, pending scope/title approval | Original orchestration, lifecycle, tests and documentation; imported expression excluded |
| gpl-build-materials | Separate GPL-compatible grant required for eligible original build scripts; exact grant pending | Build/install recipes potentially needed to reconstruct the GPL-covered output; not automatically GPL merely because they invoke a compiler |
| kwin-combination | Retain GPL-covered output obligations and original per-file MIT/GPL notices | KWin patch, injected adapters, protocol code and preparation helper; complete combined output is not PolyForm |
| mit-adapters | Existing MIT notices retained | MIT-marked files outside the KWin module; no unilateral replacement |
| upstream-patches | Retain exact applicable upstream terms | Mesa/Venus, Aquamarine, Hyprland and other patch context; no single inferred license |
| third-party | Retain applicable Apache/CC0 and reference-license terms | rvgpu header, pacstrap.conf and license copies |
| origin-review | Excluded from PolyForm pending specific evidence | Other imported helpers and upstream configuration with incomplete source-era rights |

A module may contain several applicable notices: an MIT file does not lose its
MIT notice because it participates in a GPL-covered KWin combination. Shared
adapters are listed once in review membership but can participate in multiple
build outputs. The source package must include each output's actual closure.

## Selected standard text — no addendum

The owner selected unmodified PolyForm Noncommercial 1.0.0 and declined an
additional enterprise-evaluation permission. The official copy and its SHA-256
are recorded in license-text-sources.json and modules.json. See CANDIDATE-TERMS.md
for the inactive scope/notice proposal; the standard text itself is unedited.

The standard distribution, permitted-purpose, patent and remedy provisions govern
any future approved PolyForm grant. Earlier custom-policy restrictions must not be
reintroduced through a README, required notice or module manifest. No 30-day trial
is included. The prior custom policy is historical only and stored under history/.

The GPL build-material module has a separate proposed GPL-2.0-or-later treatment
for eligible original files. Its source rights and full reconstruction closure
still require review. This proposal does not replace existing upstream notices or
activate a grant. All modules remain review-only until the owner approves scope.

## Paired GPL source delivery

For a covered compiled module, prepare the complete preferred-form source and
applicable notices with the binary, including exact upstream inputs, modifications,
interface definitions, necessary generated inputs, and build/install scripts.
Do not publish only the injected WSX files or a source URL/hash list. Apply the
actual GPL version's requirements, dependency terms and system-component exceptions.
Do not impose a PolyForm restriction on the GPL-covered source/output or required
build materials in a way that restricts the GPL recipient's rights.

Existing component packages already carry a sources.tar sidecar and bind its hash
to the runtime receipt. Rootfs payloads must carry that source material and its
receipt too; it is not enough to retain them in a separate temporary Actions job.
Material collection remains explicitly incomplete for legal source closure and
image-wide package coverage. A paired archive is necessary engineering evidence,
not a declaration that every dependency and distribution obligation is satisfied.

No binary publication gate is relaxed. No ABI, GPU pairing, synchronization,
resource retirement, guest startup behavior or upstream notice is changed.

## Implemented checks in this preparation

`audit-license-modules.py` verifies per-path module membership against the source
inventory, rejects missing mappings and rejects mapping existing or unresolved
terms to a PolyForm candidate. It can export hashes and membership into an external
audit directory without making its own report recursively part of the inventory.

Both rootfs finalizers now attach `component-sources.tar`,
`component-materials.json` and `component-source.json`. `publish.py` checks the
source-delivery set before network operations and includes it in upload/completion
verification. Missing sources, changed bytes and mismatched runtime receipts fail.
The archives still carry a pending-completeness status; no complete dependency
closure or real component compilation was established by fixture tests.

## Reconstruction dependency and product binding contract

`components/license-boundaries.json` separates KWin-only reconstruction,
paired-component building, image assembly, packaging, and preflight/delivery.
Explicit commands/data dependencies are combined with recursively discovered local
Python imports by `product_licenses.py`. Candidate-restricted helper imports in
these reconstruction paths fail the check. External package/toolchain dependencies
and dynamic behavior beyond these declared edges still require real-build review.

Original helpers and metadata needed by these paths are reserved in the separate
GPL-compatible build-material candidate group. This does not change existing
third-party terms or activate any GPL grant. Original guest code installed into
the image is recorded separately from tools used to construct it. Staging-added
executable expressions are explicitly marked as generated-output rights needing
review; a generator's proposed license is not silently applied to the result.

License-selection metadata, module rules, boundary declarations and exact reference
texts are hashed build inputs. The build emits `MODULE-LICENSES.json` and
`MODULE-NOTICES.txt` into both collected source and installed notice materials.
They record candidate status, existing per-file rule, original source hashes,
shared adapter participation, output-specific treatment and reconstruction edges.
The WGY notice remains explicitly proposed; no active Required Notice is invented.

After image staging, `IMAGE-LICENSES.json` binds the declared WSX output paths to
actual file hashes or link targets. Missing outputs and changed notices fail.
Finalizers verify this binding again before packing. These mappings exclude the
complete system-package/media closure and do not claim image-wide compliance.

### Installed package evidence

`IMAGE-LICENSES.json` also records the actual Pacman local package names,
versions and declared license values, hashes each package's `desc` and `files`
metadata, and hashes regular files under `/usr/share/licenses`. License links
are recorded as links without reading external targets. WSX component notices
are bound separately to avoid a self-referential image report.

Final packaging recomputes this evidence. Package metadata or installed notice
changes after map creation invalidate the binding. Missing package evidence is
explicitly reported; an empty database never means review completion. Malformed
identities, duplicate package names and unsafe metadata links fail collection.

This is an installed-evidence inventory, not a package license resolver or a
permission grant. Package declarations may be incomplete. The inventory does
not establish corresponding-source delivery, associate every notice with its
rightsholder, or cover unmanaged fonts, icons, wallpapers, codecs and trademarks.
A real image build is still needed to produce and review its concrete package
inventory. `license_review` remains `pending` and `distribution_allowed` remains
`false`; no package is automatically removed or relicensed.

### Enforced local source closure

Collection now requires every file in every declared reconstruction closure,
including recursively discovered local Python imports, to be present with its
current hash in the compilation receipt. The same check applies to declared
installed source inputs. Each output source pattern must match actual files;
every match must be included and unchanged. Finding just one source file for
an output is insufficient. Source symlinks and paths escaping the repository
are rejected.

These checks run before a completed material receipt can be written. They bind
the declared local dependency model to the collected recipe files. They do not
prove that the model includes dynamic commands or all external dependencies,
and do not activate any candidate license or assert legal corresponding-source
completeness. A failed collection may leave partial files for diagnosis, but
must not produce a completed material receipt or be published as complete.


## Practical review scope and stopping rule

The owner selected a bounded engineering review rather than an open-ended audit.
Keep the existing automated safeguards; do not add new generalized scanners,
per-file manual approval requirements, or speculative dependency reconstruction
without a concrete build, delivery or rights defect.

The engineering baseline is:

- Keep GPL-covered combinations and their required reconstruction materials
  outside the PolyForm scope; preserve all existing upstream declarations.
- Deliver pinned source archives, local modifications and the declared required
  build/install materials with the binary, bound by the existing receipts.
- Reject missing required files, inconsistent asset lists, changed hashes and
  ambiguous module mappings. Record remaining limitations honestly.

Passing this baseline means the delivery checks passed, not that a new license
is effective or every legal question has been resolved. The owner has not waived
applicable upstream obligations. Candidate activation and external distribution
remain distinct decisions; this scope change does not authorize either one.

After the baseline passes, prioritize a concrete private build and its actual
failures instead of expanding synthetic audit coverage. Review the resulting
package inventory and source bundle for specific omissions. Do not require a
claim of byte reproducibility or universal source completeness as a substitute
for that practical review. A known missing required source remains a defect.

Performance, application compatibility and desktop stability work remain separate
from licensing and must be backed by appropriate measurements. This repository's
scope does not authorize changes to the Windows host or other repositories.

### Reusing source-built components

Rootfs workflows now admit explicit component packages rather than compiling the
paired graphics stack on each run. The consumer and pin are in the existing
build-material candidate boundary. The original component source/license mapping
is retained and checked against current paired inputs. The delivered source
archive additionally preserves the current rootfs recipe under `rootfs-recipe/`,
with hashes and the original component-material receipt. No new grant is implied
by reuse; temporary Actions artifacts are not permanent corresponding-source
hosting. See the release protocol for pinning and failure behavior.
