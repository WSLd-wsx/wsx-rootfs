# Historical binary retirement candidates — no deletion authorized

The user expressed an intention to consider deleting historical rootfs images
and verified-components after seeing concrete assets. This is a planning record,
not an executable deletion plan. No assets, tags, releases or packages were
removed. No visibility or permissions were changed.

## Candidates identified from local repository evidence

These records are NOT a fresh remote asset listing. API asset IDs, current
visibility, current existence, exact filenames and backups must be verified
before any proposed destructive action. Do not invent missing asset IDs or
infer absence from the GitHub connector's 404 response.

| Candidate | Local locator and identity | Evidence and dependency |
| --- | --- | --- |
| CachyOS r2 rootfs archive | Historical release link: https://github.com/WSLd-wsx/wsx-rootfs/releases/tag/untagged-332d9d88866fdce8dbf9 ; later local record names wsx-cachyos-plasma-2026.11.1-r2 | docs/cachyos-validation.md; build 2091dc5bac6340325612f5d3c9c002327329e7ef; run 41269754558; 2,015,878,334 bytes; SHA-256 154e8c959cfbaadaaf58c46b44ac6458c3992b3b14a336667f58079efc2c2645 |
| CachyOS r1 rootfs archive | Historical release link: https://github.com/WSLd-wsx/wsx-rootfs/releases/tag/untagged-8f0bd477b40972ce2cd9 | docs/cachyos-validation.md; build aa195a7f46e7f257fdf08bb09d5135646e62583e; run 41265853391; 2,015,809,410 bytes; SHA-256 481b794cee452487e1da31eb796e5f5f3da6ad178b21944ccbd54c017e032488 |
| verified-components OCI object | ghcr.io/wsld-wsx/wsx-rootfs/verified-components@sha256:fbf7a09de32f616c1198191af8346f071f13c4e530580eff4289bb668fea84e9 | components/package.json; archive SHA-256 6dd87b7082bd93a330e397c8aa315b18c6f06428405be7760da930fdd6318206; currently consumed by both distro workflows |
| Component staging archive | wsx-verified-components.tar.gz; staging Release tag/asset ID not identified locally | import-components.yml uses a caller-supplied Draft tag; a matching archive would need byte verification against components/package.json |

The r2 untagged link and later logical tag must be resolved to a remote release
ID; do not assume they are two different releases. Other Omarchy rootfs releases,
partial uploads and Actions artifacts may exist but are not enumerated here.
Do not interpret this list as complete or use name patterns for bulk deletion.

## Why the component package cannot simply disappear

`.github/workflows/build-rootfs.yml` and `cachyos-plasma.yml` pull the digest
recorded in components/package.json. Removing its package version could break
both build routes. The available source builder does not supply a complete
KWin source/build closure. Replacing the historical import requires a separate,
traceable recipe revision and validation; a hash list is not a replacement.
No workflow, pin or schedule was disabled or modified during this preparation.

## Required preparation for a concrete future decision

1. Obtain authenticated, repository-scoped read access and enumerate all pages of
   releases/assets, relevant Actions artifacts and package versions. Record IDs,
   tags, status, sizes and digests; distinguish package digest from archive hash.
2. Preserve candidate bytes plus manifests, completion markers, SHA256SUMS,
   sources, component records, validation and original failure evidence in a
   dedicated archive. Verify backups and record their locations and digests.
   The existing Git bundle is not an asset or OCI-layer backup.
3. Identify earlier recipients, any source offers/commitments and applicable
   retention obligations before disposing of the only retained copy. The user
   reports no transfers to others; remote access evidence is still unavailable.
4. Decide how current build dependencies will be replaced or intentionally
   retired before removing referenced objects. Do not silently change a stable
   identity or claim an unverified replacement is equivalent.
5. Present exact asset/package IDs, current digests, backup receipts, impact and
   proposed operations for separate approval. Re-read current remote identity
   immediately before an approved operation. Never use blanket name deletion.

Deletion must not be represented as withdrawing an effective prior license,
proving no distribution occurred, or solving a corresponding-source gap. This
record preserves those questions rather than asserting a legal outcome.

## Current access and next intervention

On this follow-up, the authenticated GitHub connector again returned 404 for
WSLd-wsx/wsx-rootfs. It does not establish nonexistence. No remote assets could
be freshly listed or backed up. Supply repository-scoped read access or an exact
repository-only metadata/asset export before preparing a final deletion proposal.
The FSF GPL pages also timed out; no new legal interpretation is inferred from
unavailable pages. No deletion command has been prepared or executed.


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
