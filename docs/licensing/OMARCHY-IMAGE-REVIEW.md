# Omarchy r9/r10 practical image license review

Reviewed on 2026-11-04. This review uses the actual published archives, not just
repository declarations. Its scope is retained notices, module boundaries and
source delivery. It is not an independent investigation of every upstream
artwork, brand or contributor, and it does not grant third-party rights.

## Verified evidence

The read-only [Actions review](https://github.com/WSLd-wsx/wsx-rootfs/actions/runs/41825758180)
ran at commit `4a48034`. Both jobs passed. Archives were read only on GitHub
runners. Reports were recovered through `gh run view --log` and their SHA-256
values checked; no rootfs archive was downloaded to the local review workspace.

| Check | r9 | r10 |
| --- | ---: | ---: |
| Installed packages with declared licenses | 583 | 583 |
| Missing package-owned notice paths | 0 | 0 |
| Component notices matching the material receipt | 112 | 112 |
| Installed files/links matching the WSX module map | 619 | 619 |
| System notice entries matching image evidence | 567 | 567 |
| Regular system notice texts collected | 558 | 558 |
| Source archive entries verified | 28,075 | 28,076 |

System notice counts include shared license templates: they do not mean 567
independent package licenses have been legally approved. Package metadata,
retained system notice bytes, and the inspected Omarchy resource hashes are
identical between r9 and r10. No retired `netinstall.yaml` content was found.

Omarchy's MIT notice is present at `usr/share/omarchy/LICENSE`. The original
Guest/initialization portions retain their mapped PolyForm scope; build helpers,
graphics outputs and upstream packages retain their separate applicable terms.
There is no blanket noncommercial restriction on the rootfs.

## Practical disposition

The owner subsequently narrowed follow-up work to preserving separation from
PolyForm, rather than building a mirror of every system package's sources.
The reconstruction dependency check passes with no PolyForm-covered inputs in
the declared build closures. Existing source grants and component receipts are
unchanged. This narrowed scope does not close the separate source-delivery gap
below or waive any upstream obligation.

1. **Notice preservation and module boundaries: passed within the checks above.**
   Keep pinned upstream inputs and their notices. Do not remove packages merely
   because their metadata says `custom` or `LicenseRef`; neither label alone
   establishes a prohibited use or redistribution.
2. **System-package source delivery: not complete in the inspected release.**
   `component-sources.tar` supplies graphics-component and WSX reconstruction
   materials. Its verified inventory does not supply corresponding source for
   all installed GPL/LGPL and other source-obligation packages. The package
   version list and repository URLs in `sources.json` are useful provenance,
   not a completed source delivery mechanism. This remains a concrete gap for
   public binary distribution; changing repository visibility did not resolve it.
3. **Upstream assets: retain provenance without a second exhaustive audit.**
   Preserve Omarchy's license and font README. The icon font README identifies
   third-party marks; its embedded name records do not add a license grant.
   This review does not independently clear every image, logo or trademark and
   does not classify absence of a separate per-image notice as infringement.

One concrete source-obligation example is `libfdk-aac 3.0.0-1`, installed through
the declared dependencies of `pipewire-audio`. Its complete notice is retained
at `usr/share/licenses/libfdk-aac/NOTICE`. The notice requires free source access
for binary recipients and does not grant patent rights. This is not a finding
that the package categorically forbids commercial use or must be removed; do not
delete it independently of its audio dependency chain.

The next corrective work should establish version-matched system-package source
access and necessary build recipes/materials, with clear links alongside the
binary downloads. Merely linking the latest upstream branch is insufficient.
No byte-identical rebuilding requirement is imposed by this review. No new
written source offer or commercial license has been issued.

The public r9/r10 releases were not modified by this review. These findings do
not retroactively approve public image distribution. Existing workflow
publication guards remain unchanged.

## Primary references

- [GNU GPL FAQ: redistributing unchanged binaries](https://www.gnu.org/licenses/gpl-faq.en.html#UnchangedJustBinary)
- [GNU GPL FAQ: source and binary delivery sites](https://www.gnu.org/licenses/gpl-faq.en.html#SourceAndBinaryOnDifferentSites)
- [FDK AAC upstream notice](https://github.com/mstorsjo/fdk-aac/blob/master/NOTICE)
  (the actual installed notice was also read, independently of the moving URL).
- [Pinned Omarchy license](https://github.com/omacom/omarchy/blob/237f1b4071a0bff2296c6d740ba2b9fd695ebfa0/LICENSE)
- [Pinned Omarchy icon-font provenance](https://github.com/omacom/omarchy/blob/237f1b4071a0bff2296c6d740ba2b9fd695ebfa0/default/fonts/omarchy/README.md)

Machine reports remain available as hash-checked `LICENSE_REVIEW_CHUNK` records
in the linked workflow logs. Their evidence-present results are not legal
clearance flags. This review is engineering due diligence, not legal advice.
