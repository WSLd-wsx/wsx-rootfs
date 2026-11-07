# License completeness recheck after component producer merge

Date: 2026-11-03. Result: **not ready for licensed redistribution or a compliance
claim**. The new build route improves engineering traceability; it does not
complete source licensing, notice delivery or corresponding-source availability.
No license was activated and no commercial authorization was issued.

## Current facts, superseding earlier recipe availability statements

The current working tree now contains `scripts/build-kwin.py`, a KWin 6.8.1
archive pin, CachyOS component dependencies/build entry, source packaging and
consumption scripts, plus both component profiles in the workflows. Earlier
statements that the KWin recipe is absent describe the previous snapshot.

The new KWin builder verifies the archive and vendored adapter hashes, invokes
the retained preparation script and runs CMake/Ninja in an isolated prefix.
This is a concrete recipe, not a full compile result. No real source download,
patch application, compiler run or GPU test was performed during this recheck.
The existing vendor provenance check passes and no vendored license was removed.

The user reports extracting the producer from wsx-proto. This task did not inspect
that other repository. `merged-code-evidence.json` records changed/new paths and
current hashes relative to the previous inventory, without inventing origin
paths, original commits or source-era grants. Some entries may be new glue rather
than copied code; the list is not a claim of verbatim import. The original-work
independent-development statement remains in OWNERSHIP.md.

## Concrete open items

| ID | Finding and local evidence | Completion criterion |
| --- | --- | --- |
| R1 | CANDIDATE-TERMS.md remains NOT EFFECTIVE; grantor legal name and covered versions are blank/unapproved | Owner identifies the legal grantor and explicitly approves a completed grant for eligible original components; do not overlay it on third-party/GPL-covered material |
| R2 | New producer files have current hashes but no original path/commit/content receipt or source-era notice mapping | Supply a scoped import receipt or distinguish newly written glue; preserve any original terms; no cross-repository reads without additional authorization |
| R3 | package-source-components.py archives only private/ and component-source.json; there is no reviewed, complete notice bundle added by that packager | Deliver applicable MIT/GPL/Apache and all dependency notices with actual payloads, preserve copyright and changed-file attribution; inspect installed license files rather than assume they are present |
| R4 | build-components.py still explicitly records license_review=pending and corresponding_source_complete=false | Review exact preferred-form sources, applied patches, generated inputs, build/install scripts, dependencies and packaging materials; retain and offer the required complete source for each covered binary identity |
| R5 | Actions evidence retains some archives/receipts temporarily; no complete independently downloadable corresponding-source package or durable delivery policy exists | Produce and verify the actual source package, bind it to binary hashes and retain it under the applicable distribution obligations; a hash list is not the source |
| R6 | Rootfs/package payloads, fonts, icons, wallpaper, codecs and trademarks were not audited in this turn; CachyOS recipe still names unrar | Inspect actual versioned payloads and their license inventory; do not call the whole image open source or subject it to a blanket WSX noncommercial rule |

R1 applies to the proposed new WSX grant, not to materials already governed by
valid third-party terms. R2 is a targeted origin question, not a rejection of the
user's personal-authorship statement. Adding a generic license text alone does
not close R3, R4 or R6.

The GNU GPL v2 text (sections 2, 3 and 6) should be reviewed for the actual
KWin combined distribution and source-delivery route. No exact legal conclusion
about the entire binary closure is inferred without inspecting it. MIT permits
commercial dealings subject to its notice condition; Apache-2.0 also requires a
license copy and applicable retained notices. Source-available restrictions
cannot be described as OSI open source or replace those existing permissions.

Authoritative references:

- https://www.gnu.org/licenses/old-licenses/gpl-2.0.txt
- https://opensource.org/license/mit
- https://www.apache.org/licenses/LICENSE-2.0.txt
- https://creativecommons.org/publicdomain/zero/1.0/legalcode.txt

## Repairs performed by this recheck

1. Added readiness gates immediately before the newly introduced component binary
   uploads in components.yml and cachyos-plasma.yml. Previously those uploads
   preceded or lacked a licensing gate. Compilation/local packaging remain
   possible for inspection; uploading these candidates cannot imply approval.
2. Added a regression check for unconditional gates before both candidate binary
   upload steps. Existing rootfs/Draft/retry gates remain.
3. Added unmodified official GNU GPL v2 and CC0 legal texts as reference copies.
   The existing Apache copy remains. URLs, hashes and retrieval method are in
   license-text-sources.json. This does not apply a new license, replace a
   GPL-2.0-or-later declaration with GPL-2.0-only, or complete notice propagation.
   The GNU website timed out in the browser tool but its official plain-text
   endpoint succeeded through curl; the full copy is now locally retained.
4. Recorded new producer-origin review exceptions and regenerated path coverage.
   Current file hashes remain separate from ownership and distribution readiness.

## Remote deletion and regeneration

The user explicitly authorized deleting all wsx-rootfs Releases and attachments
and its dedicated verified-components GHCR package, after inventory and recoverable
backup. This later instruction supersedes earlier no-deletion preferences for
that scope only. Git tags, branch history, Actions artifacts, unrelated packages,
other repositories and repository visibility are not included. Do not ask for
this same scope authorization again unless the actual targets differ.

No deletion occurred: the authenticated GitHub connector again returned HTTP 404
for WSLd-wsx/wsx-rootfs; gh, gh.exe and git-lfs are unavailable in PATH. Current
release IDs, asset sets, package versions and recoverable remote backups could
not be obtained. A 404 does not prove that anything is absent. Repository-scoped
read/write access to Releases and the dedicated package is the external blocker.
Do not infer that SSH Git access permits REST Release/package administration.

Regeneration from reviewed code is the requested direction, but the premise
“licenses are complete” is not yet satisfied. No build was dispatched and no
replacement image or package was published. Deletion will not itself close the
above source/notice/ownership questions or erase prior permissions.

## Validation and preservation

Pre-edit backup: `/tmp/wsx-rootfs-license-recheck-20261103T153048/`. It contains
all tracked/non-ignored working files, SHA-256 records and a verified all-refs Git
bundle. The bundle does not include remote release assets or registry layers.
Your new producer/build/packaging code is preserved without modification; only
the two workflow upload gates and review material are changed in this pass.

Baseline unittest result: 76 tests, successful with 8 skipped. Seven package
round-trip checks need zstd, which is not installed; the metadata round-trip test
also needs root/zstd. This is materially narrower than a full archive validation.
The original licensing inventory was stale after the merge; it is regenerated
rather than treated as a passing result. Final test and review logs are retained
in the backup directory. Neither a green test suite nor an archive hash proves
license compliance or hardware acceptance.

Final local result: 77 tests successful, 8 skipped for the environment limitations
above; vendor hashes, inventory coverage, official-text hashes, workflow syntax
and diff whitespace checks passed. The readiness gate intentionally returned
nonzero. All newly merged producer source files and pins are byte-identical to
the pre-recheck backup. Remote deletion and regeneration remain unexecuted.


## Remote retirement executed

See REMOTE-RETIREMENT.md and remote-retirement.json. After gh access was restored,
the user waived further backup and requested immediate deletion. All four Draft
Releases with 19 attachments and the dedicated verified-components package were
deleted and their absence verified. Earlier access blockers and no-deletion
statements in this historical record are superseded by that execution record.
License completeness and replacement distribution remain separate open work.
