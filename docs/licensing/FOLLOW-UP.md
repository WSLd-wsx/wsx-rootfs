# Notice propagation and evidence follow-up

Status: local, uncommitted, review only. No new license is effective.

## Completed local repair

`scripts/stage-guest.py` and `scripts/stage-cachyos.py` preserve the leading
comments of the pinned session source before emitting AST-selected functions.
The generated file also identifies its source and says the staging recipe
adapted it. The original MIT declarations were not replaced, and the change does
not assert a new copyright holder or grant. Existing stage tests assert both
notice retention and adaptation attribution.

This fixes a specific lost-header defect. It does not establish complete MIT
notice compliance for an image: the corresponding full permission text, any
applicable copyright notices, other generated outputs and binary distribution
materials still require review. Nor does it retroactively alter any old image.

## Validation

- Both generated desktop Python ASTs are identical before and after the repair,
  using isolated filesystem fixtures and mocked compilation. No session/GPU ran.
- Current unittest discovery: 54 tests successful, 1 skipped. Stage assertions
  exercise actual generated outputs; existing safety/protocol checks still pass.
- Recorded vendored source hashes match; all original vendor files are unchanged.
- `git diff --check` passes. The licensing inventory is regenerated and checked.
- Explicit release-readiness check continues to fail intentionally.
- The user's pre-existing changes in docs/cachyos-validation.md and
  docs/publication-review/README.md remain byte-for-byte unchanged.

Pre-edit backup and logs:
`/tmp/wsx-rootfs-license-followup-20261103T144327/`. See original-files.json,
generated-ast-equivalence.log, unit-tests.log, provenance.log, diff-check.log,
license-check.log and release-gate.log. Previous validation records describe the
first audit snapshot; this section describes the follow-up snapshot.

## Evidence request register

| Evidence | Current status | Who can supply it / bounded next action |
| --- | --- | --- |
| Prior recipients and terms for the MIT files/outputs | User reports own controlled environments only, no transfers to others, on 2026-11-03 | Retain this statement; separately verify repository/package/release visibility when authorized read access works |
| Authority over independently authored components | User now attests personal independent development with AI assistance and no employer/client/other contributor rights; legal name blank | See OWNERSHIP.md; retain original-work exclusions and source records; supply legal identity before activation |
| Source-era license for imported helpers and upstream configuration | Local hashes and origin paths available, terms incomplete | Owner provides repository-scoped source/license export; no other repository is accessed without additional authorization |
| Historical r2 binary to source correspondence | Independent binary/patch pins, no exact mapping | Provide original source/build receipts and retained build materials; otherwise a future rebuild needs a new revision |
| GitHub releases, assets and GHCR visibility | Connector returned 404; gh unavailable in prior check | Enable repository-only read access or provide an asset metadata/export set; no publication or permissions change by this task |
| Image-wide notices and actual package inventory | Recipe lists available; payload not inspected | Obtain an authorized repository asset plus manifest/package database/licenses; review fonts/artwork/codecs/trademarks separately |
| Complete generated notice delivery | Two desktop headers fixed locally | Prepare a separately reviewed image notice bundle once exact rights and applicable source texts are established |

An asset export should identify release ID/tag, Draft/prerelease status, creation
and publication times, asset ID/name/size/digest and download time; retain original
bytes and compute SHA-256. Package evidence should include OCI manifest/layer
digests and source/build receipts. Neither an export nor a digest proves rights
or corresponding-source completeness on its own.

The confirmed policy preferences remain in CANDIDATE-TERMS.md. No additional
answers are assumed for legal identity, binary redistribution, evaluation clock
mechanics, archival retention or exact eligible component versions.


## Subsequent source migration

See SOURCE-MIGRATION.md and ../component-package.md. The current local working
tree removes historical binary build dependencies and blocks incomplete source
routes. Earlier dependency descriptions in this record refer to the pre-migration
snapshot. Remote main and assets remain unchanged; no deletion is approved.
