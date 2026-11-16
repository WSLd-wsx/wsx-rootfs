# Current-repository public-source preparation

Reviewed 2026-11-04 at base commit `5aeb31f`. The owner selected preparation of
this existing repository for public source access, with a separate review of
history handling and the r8 Draft transition. No visibility change, history
rewrite, tag change, release deletion or package visibility change is approved
or performed by this preparation.

## Upstream evidence and conservative scope

All three imported files match the recorded fixed upstream revisions byte for
byte. This is stronger provenance evidence, but the license conclusions differ:

| Local path under `distros/cachyos-plasma/upstream/` | Evidence | Treatment for the prepared preview |
| --- | --- | --- |
| `netinstall.yaml` | Exact match to `src/modules/netinstall/netinstall.yaml` at cachyos-calamares `e6c22095c3ed4e51725a7cbf9870d453462eb1fb`; no file notice or matching `.reuse/dep5` entry in the multi-license tree | Excluded; source-era license remains unresolved |
| `iso-os-release` | Exact match to `archiso/airootfs/etc/os-release` at CachyOS-Live-ISO `3215497d2e8c5fea90e185affcf973dfa2cf790b`; upstream root LICENSE supplies GPL v3 | Excluded conservatively while final file-scope treatment is reviewed; no WSX grant inferred |
| `iso-cachyos-release` | Exact match to `archiso/airootfs/etc/cachyos-release` at the same Live ISO revision and root license | Same conservative exclusion |

Primary evidence:

- [Pinned netinstall file](https://github.com/CachyOS/cachyos-calamares/blob/e6c22095c3ed4e51725a7cbf9870d453462eb1fb/src/modules/netinstall/netinstall.yaml)
- [Pinned REUSE mapping](https://github.com/CachyOS/cachyos-calamares/blob/e6c22095c3ed4e51725a7cbf9870d453462eb1fb/.reuse/dep5)
- [Pinned Live ISO license](https://github.com/CachyOS/CachyOS-Live-ISO/blob/3215497d2e8c5fea90e185affcf973dfa2cf790b/LICENSE)

`scripts/prepare-public-source.py` creates a review-only snapshot and per-file
hash manifest outside the repository, excluding these three files, `.git`, remote
assets and logs. It is deliberately not a runnable checkout: existing CachyOS
recipes and dependency metadata still reference the excluded private inputs.
It must not be uploaded or described as a fully prepared public repository.
The original checkout and byte-preserving provenance remain unchanged.

## Visible history

The baseline has ten commits reachable from main. All three paths exist in every
one of those commits. Remote refs are main and
`refs/tags/wsx-omarchy-4.0.6-r8`, pointing to
`c794098a4c38f715e2b61d3d9b5211d3f4d21452`. Removing current files alone cannot
exclude them from a public repository. The r8 tag remains an exposure path even
if the Release is returned to Draft.

Prefer resolving the upstream permission question where possible. If exclusion
is chosen, prepare isolated candidate refs, complete old/new tree and ref
differences, and the explicit disposition of the r8 tag for another review.
Do not silently retarget a built-image tag, delete history, or push rewritten
refs. Any later approved update must use freshly read old SHAs and explicit
leases. Rewriting refs does not revoke licenses or guarantee removal of hosted
old-commit URLs, cached archives, forks or other retained objects.

## Existing release and packages

The reviewed remote has one release: `wsx-omarchy-4.0.6-r8`, ID `432903498`,
currently `draft=false`, `prerelease=true`, with nine assets. The concrete proposal
is to change only `draft` to `true` before any repository visibility change,
preserving every asset ID, digest and size. This proposal is not executed.
Pre-release labels do not restrict public access once a repository is public.

Before executing that transition, re-read repository privacy, release identity,
target commit and all asset metadata. Afterward verify Draft state and unchanged
assets. Keep repository visibility private until the source-history/tag issue is
resolved; Draft state alone does not solve it. A Git bundle is not a backup of
Release assets or GHCR blobs. No deletion or binary migration is authorized here.

Both dedicated GHCR packages, `wsx-rootfs/source-components` and
`wsx-rootfs/source-components-probe`, were confirmed private. Keep their visibility
private independently of any repository change.

## History and log review

Reviewed all 262 distinct blobs in the ten currently reachable commits and all
twelve currently available Actions log archives (34 log members). The scan found
no matches for GitHub tokens, AWS access keys, private-key markers, credential URLs
or the selected literal-secret assignment pattern. The fifteen Authorization
header occurrences were masked. Password-related text consisted of account-lock,
test or package-description/build-status contexts; no exposed password was identified.
There were no Actions Artifacts at the metadata snapshot and no listed pull
requests. This is a bounded review, not proof that all possible secrets are absent;
deleted/expired or otherwise unavailable material is outside the evidence set.
Raw logs and per-blob evidence are kept only in the external task audit directory.

## Workflow behavior prepared locally

- Public and private repositories can run source contract checks with read-only
  repository permission. This is not a legal publication approval.
- Binary/component/rootfs jobs check live repository identity and visibility
  before expensive operations. Public manual attempts fail explicitly in
  source-only mode; public scheduled Omarchy binary builds are skipped.
- Diagnostic upload steps require successful private-build admission, including
  steps previously using unconditional `always()`.
- Existing payload, license, private GHCR and private Pre-release guards remain
  active. Source visibility never implicitly approves binary redistribution.

The upstream license evidence, complete ref/asset plan, raw logs, hashes and
verified pre-change Git bundle are in the dedicated external audit directory
recorded in the task report. The current source grants and full-image distribution
limitations remain unchanged.

## Superseding owner decision: remove the old Release

After the initial Draft proposal, the owner authorized removal of the online r8
Release, stating that a complete local r8 copy exists. Release `432903498` and its
nine assets were deleted; a subsequent API read returned zero releases. The local
binary backup was not independently inspected under the current filesystem scope.
The original asset IDs and hashes remain in the external evidence inventory.

The r8 Git tag remains at `c794098a4c38f715e2b61d3d9b5211d3f4d21452`;
its source-history exposure is unchanged. The two GHCR packages were not modified.
The pinned Omarchy component digest remains present, and all 87 required current
component/policy inputs match its original source receipt. No component rebuild
is required for these preparation changes. The next Omarchy 4.0.6 recipe revision
is r9 to avoid reusing the retired r8 publication identity.

Removal does not clear public licensing or authorize public binaries. Original
component source bundles still include the unresolved imported recipe materials;
private reuse is distinct from public source/binary distribution review.

## r8 source history and Omarchy source delivery repair

The local delivery repair filters only the three reviewed CachyOS imports from
`recipe/` and `rootfs-recipe/` inside future Omarchy source attachments. Exclusions
require exact reviewed SHA-256 values; changed bytes or disagreement with the
material index fail delivery. Other upstream source archives, patches and license
files remain included. The copied material report records each exclusion and the
original source archive hash. Original private GHCR bundles are not modified.
CachyOS delivery is not filtered: these inputs still require resolution there.
This does not certify complete corresponding source for the whole rootfs.

An isolated historical candidate was prepared in the external task audit directory
`/tmp/wsx-rootfs-source-history-20261104/`. All ten commit trees were compared:
only the three imported paths were removed from each candidate tree. The candidate
main tip is `212b485e6fda662289985fd2294599b0d1be93ca`, compared with original
`5aeb31f7cb0cc671477ba936c7f256eb7ca66219`. The candidate excludes current
uncommitted preparation changes and is not a runnable or publication-approved
checkout: CachyOS recipes and provenance still reference omitted inputs. Its
`refs/original` deliberately preserve the old trees for review. Do not push the
candidate repository wholesale.

The live r8 tag still identifies the old tree at
`c794098a4c38f715e2b61d3d9b5211d3f4d21452`. The proposed treatment is to retire
that tag, not retarget it to different sources under an old binary identity.
Deleting it alone cannot remove the same files from main history. Before any live
history/ref change, resolve the current CachyOS source scope, incorporate the
reviewed working changes, show the final old/new refs and tree differences,
re-read remote SHA values and obtain approval for those concrete operations.
No live ref rewrite or tag deletion was performed by this preparation.

The two ISO identity files have upstream repository-level GPLv3 evidence; the
Calamares netinstall configuration lacks a confirmed applicable file-level grant
in the reviewed multi-license metadata. None is silently relicensed by WSX.
Omitting these unrelated files from Omarchy delivery resolves their accidental
inclusion there, not their licensing status or their presence in Git history.

## Superseding CachyOS input resolution

The previous three-file exclusion and ten-commit filtering candidates are obsolete.
The current tree retains the two ISO identity files unchanged and assigns their
upstream treatment to GPL-3.0-only, based on the exact pinned upstream root LICENSE
retrieved through the GitHub contents API. The complete license is now retained
in `docs/licensing/licenses/upstream/cachyos-live-iso-LICENSE`; `source.json`,
LICENSE-MAP, third-party notices and module rules record this evidence. This is
retention of upstream terms, not a WSX grant. Trademark clearance is separate.

The unused `netinstall.yaml` reference was moved to the external audit backup.
The actual rootfs package selection remains in `packages.txt`, unchanged. Its
source lock entry and declared dependency were removed. Historical references in
review records describe past facts and do not include the retired YAML bytes.
The two-profile source delivery projection now removes only the exact retired
netinstall bytes from copied old bundles. Identity sources and the newly retained
license are included in the current rootfs recipe portion.

Changing policy files makes the old component receipt fail the existing exact
policy admission check. Do not disable that check or claim the old package is
already admitted. Compiler source inputs have not been changed by this repair.
A separately validated metadata/source repack or a bounded policy transition is
needed before reuse under the new policy; this is not intrinsically a reason to
recompile Mesa or the compositors. No registry package was changed here.

The proposed final history route is a new single-root snapshot of the reviewed
current tree, retaining both licensed identity files and excluding netinstall,
with deletion of the old r8 tag (never retargeting that old release identity).
The exact candidate commit and tree diff are recorded outside the repository to
avoid a self-referential commit ID. Candidate preparation does not authorize
pushing, changing visibility, publishing binaries or removing server-side caches.
Original Git history and retired file bytes remain in the external audit backup.

## Bounded component policy transition

The local reuse path now supports the exact Omarchy package described in
`components/policy-transition.json`. Admission binds the immutable package pin,
original receipt digest, canonical original module-map digest and complete old/new
policy hash sets. Both original and current component reconstruction inputs and
original output source inputs must still match the compilation receipt. Unknown
policy changes, changed compiler inputs and changed pins fail without rebuilding.

After normal package verification, only the staged copy receives current notices
and a separately labeled policy transition. Original notices and material metadata
are retained under `notices/policy-transition-original/`; the original compilation
receipt and binaries are unchanged. The source archive retains original entries
and adds current policy files, transition evidence and notices. The image receives
these notices through the existing staging path. The private artifact gate verifies
the transition again and still requires the current exact policy and private
repository. The final delivery projection removes the retired netinstall bytes.
No GHCR write, graphics compilation or public distribution is performed.

Local validation covers fixture rejection cases and the actual original receipt
with a deterministic reconstruction of its original module map. The integration
archive is reduced synthetic source material, not a downloaded GHCR payload.
This environment lacks Docker and zstd executables, so full registry fetch/extract
and a remote rootfs run remain untested here. The next normal private rootfs run
will exercise the original package verification before this transition.

This implementation supersedes the earlier local metadata-transition blocker.
CachyOS has no approved reuse pin and is not silently admitted through the Omarchy
exception. Prior single-root candidates predate this implementation and must be
regenerated before requesting approval for a concrete history replacement.
