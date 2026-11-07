# Private artifact policy

Owner-approved on 2026-11-03. Source grants are effective independently of binary
publication. In the private WSLd-wsx/wsx-rootfs repository, authenticated Actions
artifacts may retain component and rootfs test binaries for the owner's testing
and reuse. They must include paired source/build materials and notices. This is
an operational approval, not an extra permission or restriction in PolyForm.

`test_only=true` remains compile/validate plus source diagnostics, with no binary
upload. `test_only=false` allows private artifact retention after the private gate
passes. The gate checks actual repository privacy, the approved source-license
state, collected source/notice integrity and the component or rootfs payload.
Artifacts from inactive-license commits are not selected as final component pins.

No public Release, public artifact workflow, image promotion or external binary
distribution is approved. Rootfs workflows stop after private artifact upload;
Draft/public publication and publication retry paths are disabled in this policy.
Changing repository visibility does not authorize uploads: the private gate must
fail. Existing downloaded copies cannot be recalled by changing visibility.

Known unresolved CachyOS upstream configurations and full-image package/asset
review are external-distribution blockers when included. They do not prevent the
owner's private builds, nor cancel grants on independent WSX expression. Reports
must distinguish source grants, private testing permission, collected evidence,
and actual corresponding-source/public distribution review.

Actions retention is temporary. A reusable component package is selected by exact
run/GHCR digest/source commit and manifest hash (or a legacy artifact ID). Expired or missing packages fail;
there is no fallback to historical verified-components or unpinned binaries.

Private GHCR component images are also approved storage under the same gates.
Their payload includes the paired source archive and notices. Visibility must
remain private; registry delivery does not grant public distribution approval.
