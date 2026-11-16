# Local validation record

Executed on 2026-11-03 against HEAD ed7a9827ade026e828f4f0124c5261b46cdb2103
plus pre-existing user changes and the new review files. No device testing,
image build, WSL boot, GPU first frame or desktop acceptance was performed.

- `python3 -m unittest discover -s tests -v`: 54 tests, successful, 1 skipped.
- `python3 scripts/check-provenance.py`: recorded vendored hashes match.
- `python3 scripts/audit-licenses.py --check`: inventory matches current files;
  source indexes from both provenance files and CachyOS upstream record match.
- `--require-release-ready`: intentionally exits 1; evidence does not authorize
  release. No publishing workflow was invoked or changed.
- Negative rule checks: uncovered path rejected; equal-priority overlap rejected.
  Rule bytes restored after tests.
- Priority MIT history: all twelve current hashes equal their path introduction
  blobs and already contain MIT there. No conclusion about public grants follows.
- All original tracked/non-ignored file bytes match the dedicated backup,
  including existing user modifications. Existing notices remain untouched.
- `git diff --check`: passed for tracked changes. New files are review material
  and a standard-library-only inventory tool; no runtime paths changed.
- Git bundle verification succeeded; remote main was independently read.

Logs reside in `/tmp/wsx-rootfs-license-audit-20261103T143643/`:
unit-tests.log, provenance.log, license-check.log, release-gate.log,
rule-negative-tests.log, preservation.log, diff-check.log and
bundle-verification.txt. The generated inventory covers the review documents
but excludes itself. Keep the dedicated external backup beyond /tmp cleanup.

The current local inventory and checks do not verify remote assets, historical
binary/source equivalence, ownership, prior grants or payload-wide compliance.
