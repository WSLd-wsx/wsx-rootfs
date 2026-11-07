# Source migration review — 2026-11-03

The user authorized local removal of historical binary dependencies and
refactoring toward source compilation. This did not authorize remote dispatch,
publication or deletion. The original scope remains wsx-rootfs only.

## Implemented changes

- Removed historical OCI/archive retrieval from both distro workflows and package
  read/write permissions. Retained the exact old pin under history/ for audit only.
- Retired the binary importer and import workflow with explicit errors, not a
  successful no-op or silent fallback.
- Connected Omarchy's source fetch/build/assembly route with per-build receipts.
  No historical GPU evidence is copied into new outputs.
- Made the incomplete CachyOS source route fail early with a concrete KWin gap.
- Preserved automatic pruning inputs for source review; no build material was
  deleted here. Added workflow publication gates while the review is unresolved.
- Updated revision selection and component provenance to identify new source
  inputs instead of an old binary archive. Existing public release rules remain.

The source path is an engineering candidate, not a verified compliant replacement.
It needs an actual isolated compile, source/notice closure review and hardware
validation before making stronger claims. Permanent corresponding-source hosting
and a complete source payload are not implemented by temporary Actions artifacts.
Original license headers and vendored hashes remain unchanged.

## Relationship to the retirement proposal

BINARY-RETIREMENT.md describes the dependency state observed before this change.
In the current working tree, those executable dependencies are removed. Remote
main is unchanged because nothing was committed or pushed; remote workflows may
still depend on the old package. Therefore this local migration alone does not
make remote deletion safe. Verify the deployed recipe revision, exact asset IDs,
backups and obligations before any separately approved disposal.

## Backup and validation

Pre-edit snapshot: `/tmp/wsx-rootfs-source-migration-20261103T150638/`, with
original-files.json SHA-256 records. All earlier user changes were retained.
No external repository, desktop, service or real device was accessed.
Logs in that directory record current tests and static checks. Source-build tests
use isolated fixtures and mocked compiler invocations; they do not download or
build the actual graphics stack. No remote success is claimed.


## Origin of the replacement code

This migration did not extract the historical verified-components producer from
another repository. It reuses the source builders already vendored inside
wsx-rootfs and the existing scripts/build-components.py, plus a new local
assembly/receipt step. It does not recover or attest the historical package's
original generation procedure. The KWin source recipe is still absent.

## Final local checks

The full suite now runs 68 tests successfully with 1 skipped. YAML parsing and
inline Bash syntax checks cover all workflows; distro shell syntax and Python
AST checks pass. actionlint is not installed, so no actionlint result is claimed.
Vendored provenance hashes, original user changes and the byte-identical archived
package pin are verified. The licensing inventory is regenerated and checked;
release readiness remains deliberately false. No actual source compilation or
remote run was performed.

The inventory tool now records pending tracked removals separately, so moving the
retired package lock does not hide the deletion or break current-file coverage.
Tests also reject uncovered new paths and dangling links.

## Subsequent CachyOS recipe integration

The missing recipe described above has now been implemented in build-kwin.py and
the CachyOS component builder. See ../component-package.md for the package admission
path and exact validation scope. This supersedes the earlier unconditional source
support rejection; it does not supersede publication review or claim successful
full compilation, source-license closure or GPU acceptance.


## Post-merge recheck

RECHECK.md supersedes earlier current-state claims: KWin compilation/packaging
code is now present, but licensing completeness is not established. The user
has now authorized retirement of all wsx-rootfs Releases/attachments and its
dedicated verified-components package after inventory and recoverable backup.
Execution is blocked by remote API access, not by missing scope authorization.
No deletion, dispatch or publication occurred in this recheck.
