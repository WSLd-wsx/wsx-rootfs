# Fresh repository source review

This record supersedes earlier migration and package-transition plans for the new
repository. The owner selected `WSLd-wsx/wsx-rootfs-private` for the original
private repository and `WSLd-wsx/wsx-rootfs` for a separately created repository.
The new repository must receive only a new root commit of the reviewed current
files, not a fork, mirror, or copy of the old Git object database.

## Source scope

Original independent Guest expression uses unmodified PolyForm Noncommercial
1.0.0 under the effective owner notice. Build/reconstruction expression uses
GPL-2.0-or-later; existing MIT, Apache, CC0 and upstream patch notices are retained.
The two unchanged CachyOS identity files retain the pinned upstream GPLv3 terms.
The unused netinstall YAML is absent; its old blob must not resolve through the
new repository API. Hashes and historical references in audit records do not
carry the old file bytes or constitute permission to distribute that file.

RVGPU source matching and NOTICE availability were rechecked against the complete
fixed official upstream tree; see `../licensing/rvgpu-source.json`. Source rule
coverage, retained notices, reference-text hashes and build boundaries are local
checks, not a guarantee of legal ownership or complete binary compliance.

## Fresh component builds

Both entries in `components/reuse.json` are empty. The old fixed package and its
policy-transition exception are removed. Missing pins fail explicitly: rootfs
assembly cannot silently consume an old package or trigger a hidden rebuild.
Build each desired profile from the pinned upstream archives, review the paired
source/notices and then record the new package's exact origin and digest.

New packages use `ghcr.io/wsld-wsx/wsx-rootfs/graphics-components`, distinct from
the old private `source-components` package. Original packages and build evidence
stay with the old private repository; they are not copied into the new public
scope. Keep the new repository private during the initial remote build review.

## Publication decisions

Source repository visibility and binary distribution are separate decisions.
Current public-source mode allows source contract checks but blocks component,
rootfs and diagnostic publication jobs. Making the repository public before
changing that policy intentionally stops binary builds; a Pre-release label does
not make binaries private in a public repository.

Public rootfs distribution still needs review of the actual installed packages,
notices and source delivery, including non-free packages such as unrar, fonts,
icons, wallpapers and trademarks. Recompiling alone does not clear these rights.
No blanket noncommercial restriction applies to the complete rootfs or upstream
GPL/MIT/Apache portions. The license scope does not promise exclusive control of
all WSX functionality or prohibit independent implementations.

Before changing visibility, verify the new repository ID differs from the old
one, the new Git graph has one root, the retired blob is unavailable in that
repository, no old Releases/Artifacts/runs were transferred, and package visibility
is private. Review any new build logs and attachments separately. Hardware testing
and a complete image-distribution decision are outside source-only clearance.
