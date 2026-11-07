# Repository licensing audit — 2026-11-03

## Scope and preservation

Only wsx-rootfs and this task's dedicated external audit directory were accessed
for local evidence. No reference repository was read. HEAD, local main and
origin/main are `ed7a9827ade026e828f4f0124c5261b46cdb2103`. A successful read-only
`git ls-remote --refs origin` also returned this main ref and no others at query
time. This does not enumerate GitHub attachments, hidden refs, forks or clones.
Remote: `git@github.com:WSLd-wsx/wsx-rootfs.git`.

Original uncommitted `docs/cachyos-validation.md` and
`docs/publication-review/README.md` were preserved without edits. The original
tracked/non-ignored tree, per-file SHA-256, binary diffs, local refs and verified
all-refs bundle are in `/tmp/wsx-rootfs-license-audit-20261103T143643/`.
`original-files.json`, `bundle.sha256` and `bundle-verification.txt` identify the
backup. This is not a backup of release assets, registry layers or LFS objects.
The temporary directory should be retained elsewhere before routine /tmp cleanup.

## Findings and three review groups

`inventory.json` is the per-file review list for all three groups, with hashes,
local history, source mappings, grounds, limitations and next actions. The rules
are conservative review decisions, not automated conclusions from strings.

1. **Retain original**: all twelve MIT-marked files, upstream patches/context,
   rvgpu Apache header and pacstrap CC0 declaration. No declaration was removed.
   Prior public grant remains unproved; preservation does not assert it occurred.
2. **Conditional future license**: independent rootfs orchestration, tests,
   lifecycle implementation, recipes and original documentation are candidates.
   Their local history is available; ownership/assignments are not. Exclude
   imported/extracted expression, upstream assets and combined covered outputs.
   The Omarchy-wsl reference record establishes reused patterns, not an ownership
   clearance of every recipe fragment.
3. **Insufficient evidence**: unmarked imported WSX helpers and imported CachyOS
   YAML/identity files. Local provenance closes byte identity, not permission.
   Required evidence is specifically source-era terms, contributor authority and
   derivation records; do not merely ask for another hash list.

No blanket repository license existed in the initial enumerated tree. Fifteen
files have SPDX markers (twelve MIT, one GPL patch, one Apache header, one CC0
config). Additional copyright contexts occur in three Mesa-related patches.
No Cargo manifests or npm dependency metadata were found. Embedded generated
shell, Python/configuration and Wayland code must follow their actual origins.
The new Apache full-text copy supplies an existing notice requirement; it does
not newly license this repository.

## Priority MIT history and combination review

All twelve files retain their initial path content in the available local
history; each has one path-specific introduction commit. Git rename/copy
similarity is not origin evidence (the Plasma entry resembles the earlier guest
entry). Full hashes and commits are in the generated inventory and priority list.

| Files under vendor/wsx-proto | First local introduction | Build relationship |
| --- | --- | --- |
| device-host/production/start-guest.py; input/guest.c | 4865a3e47526276265b742cb0773e93656ec1bf8 | Session functions extracted by stage-guest; C input guest compiled with rvgpu header |
| device-host/production/start-cachyos-plasma.py | 606a2878a6b8fa6f35611f53b986a7494435d900 | Session functions extracted by stage-cachyos |
| guest-compat/linear-depth-segregation.patch | 8c3dd8a4d9722055d2a7541d652741b6693a2959 | MIT marker in added Mesa code, not a license for all patch context |
| guest-opaque/gbm-descriptor.c, gbm-descriptor.h, wsx-opaque-uapi.h, wayland/wsx-opaque-buffer-v1.xml | 8c3dd8a4d9722055d2a7541d652741b6693a2959 | Copied into compositor builds; XML generates protocol source; also copied into KWin |
| guest-opaque/kwin-framebuffer.c, kwin-framebuffer.h, kwin-native-buffer.h, kwin-wayland.inc | 21c9e0953b533e751497e251753c6584192f3be4 | prepare-kwin copies these into src/wsx; patch compiles/includes them in KWin |

`docs/provenance.json` maps every priority file to source paths, reference commits
and working-tree hashes. KWin-related files are additionally indexed by
`components/cachyos-provenance.json`. These are local records, not a fresh audit
of the origin repository. WGY's Git identity is not ownership evidence. User
records are needed for assignments, collaborators, employment obligations and
previous recipients/terms; local history supplies introductions and byte changes.

## Corresponding source and rebuild gaps

| Input | Available evidence | Missing evidence / action |
| --- | --- | --- |
| components/package.json | OCI digest and archive SHA-256 | Historical binary transport only; retain complete source/build closure independently of GHCR |
| components/sources.json | Mesa 26.1.8, Venus 26.2.4; pinned Aquamarine/Hyprland/udis86/glaze archives | Exact retained archives, all transitive source and licenses, build environment/toolchains and outputs |
| components/cachyos-provenance.json | Ten patch/adapter hashes, reference 3199b15d; scope explicitly separates historical binary | KWin 6.8.1 full source, packaging patches, generated inputs, build commands/dependencies/toolchain, installation recipes and exact binary mapping |
| docs/provenance.json | Vendored mappings and references to unavailable source records | Non-vendored locks are references, not available corresponding source; origin authority and grant evidence |
| scripts/build-components.py | Source build route for Mesa/Venus/Aquamarine/Hyprland | Does not build KWin or prove historical r2 binary correspondence |
| distros/omarchy/build-components.sh and workflows | Import historical verified-components binary | Actual default path is binary admission; source pin list is not proof of rebuildability |

A complete source package must include the preferred modification form, applicable
interface definitions, scripts controlling compilation/installation and required
license materials for the actual covered distribution. Determine exact scope
against applicable terms. Preserve old candidates and failures; a new traceable
build is a new revision, not retroactive evidence for r2. No source or binaries
were copied from another repository and no build/download of a rootfs was run.

## Image and remote evidence limitations

`distros/cachyos-plasma/packages.txt:93` and upstream netinstall.yaml include
unrar. That verifies recipe inclusion only. Previous r2 payload observations are
historical user-supplied evidence, not revalidated here. Need the authorized
rootfs asset, exact package database/versions, license files and asset inventory
to review actual fonts, icons, wallpaper, codecs, bundled apps and trademarks.
Do not claim the full image is open source or subject to a WSX commercial ban.

Neither gh nor git-lfs is installed in the current PATH. Authenticated GitHub
connector get_repo returned 404 for this repository. The initial sandbox Git
query failed DNS; the authorized escalated read succeeded. No credentials were
printed or inspected. A 404 is not proof that the private repository or releases
are absent. Remote releases/assets, Actions artifacts and GHCR payloads were
not enumerated or backed up. Minimum intervention: provide repository-scoped
read access through the connector/gh or a repository-only release/asset export.
No changes to visibility, permissions, workflows, releases or remote refs occurred.

## Decisions and remaining review

Confirmed policy preferences are in CANDIDATE-TERMS.md: 30-day nonproduction
enterprise evaluation; stop or obtain authorization on expiry; indefinite
commercial restriction; noncommercial modification and source redistribution
with notices/restrictions; binary redistribution undecided. Legal rightsholder
is blank. Evaluation clock/reset/archive details are proposals, not confirmed.

Before activation: establish ownership and earlier grants; approve exact eligible
components/versions; review redistribution/evaluation mechanics and legal terms.
Before distribution: close corresponding-source and payload notices, fix/check
generated notice propagation, and retain remote assets. No current review output
claims release readiness. Existing CI is unchanged and does not enforce this
new local licensing review. This is engineering evidence, not a legal opinion.


## Local follow-up: notice propagation

The two staging generators now copy leading source comments before extracted
code and identify the adapted source path. Existing MIT declarations and all
vendored bytes remain unchanged. Both generated Python ASTs equal those from
the pre-change generators under isolated fixtures. Existing stage tests now
assert the MIT header and adaptation provenance. No ABI, graphics negotiation,
resource retirement or lifecycle behavior changed. This change is uncommitted
and has not been built into or distributed as an image.

The user reports that the twelve MIT-marked sources and containing binaries/
images were used only in environments under their control and were not given
to others. This is a dated user statement, not independently verified remote
visibility or an ownership/assignment record. It reduces the reported recipient
scope but does not justify deleting notices or asserting that no effective grant
could exist. GitHub assets and GHCR access history remain unverified.

Follow-up backup: `/tmp/wsx-rootfs-license-followup-20261103T144327/` contains
pre-edit file copies and SHA-256 records, including the first audit's documents.
The original all-refs bundle remains in the first audit directory. Neither is
claimed to preserve remote attachments. See FOLLOW-UP.md for validation and
remaining evidence requests.


## Ownership and retirement preparation

See OWNERSHIP.md and ownership-evidence.json for the subsequently supplied
independent-development statement. It applies only to original WSX portions,
not upstream code or all combinations. Legal identity remains blank.
BINARY-RETIREMENT.md lists locally evidenced historical binary candidates and
current build dependencies. The user intends to consider retirement after exact
assets are listed; no deletion has been authorized or performed. The GitHub
connector still returns 404, so this is not a verified remote asset inventory.


## Subsequent source migration

See SOURCE-MIGRATION.md and ../component-package.md. The current local working
tree removes historical binary build dependencies and blocks incomplete source
routes. Earlier dependency descriptions in this record refer to the pre-migration
snapshot. Remote main and assets remain unchanged; no deletion is approved.


## Post-merge recheck

RECHECK.md supersedes earlier current-state claims: KWin compilation/packaging
code is now present, but licensing completeness is not established. The user
has now authorized retirement of all wsx-rootfs Releases/attachments and its
dedicated verified-components package after inventory and recoverable backup.
Execution is blocked by remote API access, not by missing scope authorization.
No deletion, dispatch or publication occurred in this recheck.


## Remote retirement executed

See REMOTE-RETIREMENT.md and remote-retirement.json. After gh access was restored,
the user waived further backup and requested immediate deletion. All four Draft
Releases with 19 attachments and the dedicated verified-components package were
deleted and their absence verified. Earlier access blockers and no-deletion
statements in this historical record are superseded by that execution record.
License completeness and replacement distribution remain separate open work.
