# Effective modules and delivery checks

The owner activated the module grants on 2026-11-03. See the root LICENSE-MAP.md
for directory defaults, explicit helper paths and third-party exceptions, and
OUTPUT-LICENSES.md for embedded-expression and generated-output grants.

The existing dependency checks keep required reconstruction materials outside
PolyForm. Each declared required source must appear unchanged in the compilation
receipt; partial output-source coverage fails. Sources, receipts and notices are
paired with binary packages and rootfs payloads. Actual installed paths, package
metadata and license texts are recorded and checked before packing.

These checks establish the declared engineering baseline, not universal legal
source closure, byte reproducibility or hardware acceptance. Do not expand audits
without a concrete defect. Known unresolved external material blocks external
payload clearance when included; approved independent grants remain effective.

Components build independently; rootfs consumes a pinned compatible component
package and appends its current assembly recipes to delivered source evidence.
Private artifact uploads are allowed under PRIVATE-ARTIFACTS.md; public publishing
is not authorized. Previous review-only plans are retained under history/.
