# Local prebuilt component admission audit

The component-package assembly route is approved by the user. Prefer reusable
private binary packages over rebuilding unchanged graphics components for each
rootfs. Keep the four logical components separately identifiable, with a paired
bundle lock: Mesa/Zink/GBM, Venus ICD, Aquamarine and Hyprland. Session/network
adapters remain versioned recipe inputs. Windows host and kernel modules belong
to wsx-core and are not part of this rootfs bundle.

## Read-only reference audit

Reference: wsx-proto, artifacts/venus-rutabaga, inspected 2026-10-31.
The reference tree and running desktop were not modified.

| Directory | Checked manifest entries | Result |
| --- | ---: | --- |
| opaque-consumer-mesa-01 | 59 | All current prefix hashes match |
| opaque-consumer-venus-01 | 2 | All prefix hashes match, but prefix is stale relative to subsequent build |
| opaque-consumer-aquamarine-01 | 22 | All adapter receipt hashes match |
| opaque-consumer-hyprland-01 | 516 | All adapter receipt hashes match |

The four representative runtime ELF files have no DT_RPATH or DT_RUNPATH.
This is not a complete relocation or dependency acceptance test. Hyprland needs
specific shared-library ABIs, including libaquamarine.so.14, Lua 5.5, glslang 16
and Abseil 2608.0.0; arbitrary rolling distribution libraries cannot be assumed
compatible. Assembly must check the complete dependency and symbol closure.

The Venus prefix library SHA-256 is
`8c40dd3abec1fc4546e33e2f9ae82553c0d7f2f73d8d576405a333f2dc3a6270`.
The build-tree library SHA-256 is
`0e5d58384af1bdea69896d7137da0370fc9b4da522226cc63a345dab961a6752`.
`opaque-consumer-start-02/venus-query-build.log` records rebuilding that tree;
`opaque-consumer-start-03/build-result.json` records the later opaque-query patch.
The old prefix manifest does not attest the later binary. Do not upload the old
prefix as the complete desktop-verified closure or silently substitute a newer
binary under its manifest. Reconcile the later deployment receipt and source
closure first, or rebuild the pinned source recipe and label its scope honestly.

## Actual validation scope

- omarchy-406-start-01/result.json: v4.0.6 visible desktop, shell ping, menu IPC
  exit 0 and 1693 presentations; bounded startup, not stability acceptance.
- opaque-consumer-start-03/result.json: RTX 3080 Ti opaque desktop, 841 successful
  native presentations, paired producer ABI 1 / consumer ABI 2; not stock-service,
  clean teardown, physical Iris regression or indefinite stability acceptance.
- opaque-consumer-01/result.json: compilation and preparation only. Its original
  loaded kernel rejects the candidate; this is not successful desktop evidence.

These records do not automatically attest every file in today's source tree.
Keep original failures and do not package the known-bad kernel module.

## Package transport and admission

Use repository-linked private GHCR component packages, addressed by immutable
OCI digest plus per-file SHA-256 and a versioned paired-component manifest.
Publishing from a dedicated Actions job with contents: read and packages: write
avoids requiring a local registry token. Consumers need packages: read. Link the
package to this repository, preserve its private visibility, and verify actual
organization permission before treating upload as successful. Do not overwrite
published component identities or make a rootfs Draft public.

A local import needs explicit source/build receipts, the exact runtime payload,
metadata and dependency validation, and a transfer with verified checksums.
Local absolute paths are provenance only, never CI runtime dependencies.
Components without sufficient evidence must be rebuilt from the vendored pinned
recipe. Build success, dependency checks and historical hardware evidence remain
separate fields; assembling a new rootfs still requires new WSL/GPU acceptance.

GitHub documentation:
https://docs.github.com/en/packages/managing-github-packages-using-github-actions-workflows/publishing-and-installing-a-package-with-github-actions

No local component has been uploaded or admitted as a complete reusable bundle
by this audit. The running rootfs build remains independent of this investigation.

## Final deployment trace (additional audit)

`opaque-consumer-start-02/result.json` records the actual rejected OPTIMAL query;
`venus-query-build.log` records recompilation of the Venus build tree.
`opaque-consumer-start-03/build-result.json` identifies the corrected query patch
and the `venus-opaque-consumer-03` deployment. Its compositor journal identifies
`guest/venus/virtio_icd.json` in that deployment as the loaded ICD manifest.
The start-03 result records 90 verified candidate files and a successful bounded
RTX desktop, but does not contain the corresponding 90 individual file hashes.
The start-01 candidate-verification.json also reports 90 files, but refers to the
older `venus-opaque-consumer-01` and cannot attest the later deployment.

The final deployment directory was not found at its recorded path or by a bounded
name search under /mnt/wsl/u and /mnt/d. Consequently neither the final ICD hash
nor the other 89 deployment hashes can be mapped to the currently retained local
prefixes. The current build-tree hash is an observation, not proof of the bytes
loaded during start-03. A copy of the final deployment and its original per-file
manifest or equivalent signed receipt is required to close this exact mapping;
otherwise a fresh pinned build must remain a new, unverified-on-hardware candidate.
