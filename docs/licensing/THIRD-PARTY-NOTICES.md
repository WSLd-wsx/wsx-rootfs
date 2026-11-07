# Third-party notices — retained terms; public image review incomplete

Existing file notices remain authoritative and unchanged. This index neither
relicenses materials nor establishes that a recipient previously received a
grant. See `inventory.json` for exact file hashes and notice locations.

- `vendor/rvgpu/include/librvgpu/rvgpu-protocol.h`: Apache-2.0;
  Copyright (c) 2022 Panasonic Automotive Systems, Co., Ltd. Preserve the header.
  An unmodified [official Apache text](https://www.apache.org/licenses/LICENSE-2.0.txt)
  is stored in `licenses/Apache-2.0.txt`. Its hash is in the inventory. The header is byte-identical to upstream revision
  `7d29a7308a600318b1f1d957e81bf2046bf031ea`; no changed-file attribution is needed.
  The complete upstream tree has LICENSE.md and no separate NOTICE file.
  See `rvgpu-source.json` for fixed source and evidence references.
- Twelve MIT-marked files are enumerated in rule `existing-mit`. The Wayland XML
  says “Copyright 2026 WSX contributors”; this does not identify a legal owner.
  The [MIT text](https://opensource.org/license/mit) permits commercial dealings
  subject to its notice condition. Do not substitute a new restriction for an
  effective existing grant. A complete distribution notice bundle is still needed.
- `kwin-opaque-consumer.patch` retains GPL-2.0-or-later context and the upstream
  Vlad Zahorodnii copyright. The patch compiles adapters and generated Wayland
  protocol code into KWin. Recover exact upstream notices and corresponding
  source; the recheck obtained the official full GPL v2 text by curl after the browser
  request timed out. The reference copy in licenses/GPL-2.0.txt does not replace
  the existing GPL-2.0-or-later declaration or prove the complete source closure.
- Other patches retain Collabora, Intel and NXP copyright contexts where present.
  Do not infer one universal license for Mesa, its subcomponents or compositor
  dependencies from the project name or patch authorship.
- `pacstrap.conf` declares CC0-1.0; the official full text is now retained in
  licenses/CC0-1.0.txt. The two unmodified CachyOS ISO identity files retain
  GPL-3.0-only under the pinned Live ISO root LICENSE, copied verbatim to
  licenses/upstream/cachyos-live-iso-LICENSE; upstream/source.json records the
  exact commit and file hashes. No right to trademarks is inferred. The unused
  netinstall reference was removed from the active tree without assigning a license.

The repository contains no Cargo manifest or npm package manifest. The file
`docs/licensing/history/component-package.json` is a retired OCI/archive pin, not npm metadata; active builds do not consume it.
Builds fetch or install much more than the vendored tree: Mesa/Venus, Aquamarine,
Hyprland, udis86, glaze, KWin, distro packages and Omarchy configuration/assets.
Their complete notices are not present here. System packages, fonts, icons,
wallpapers, codecs and trademarks need payload-level review independently.

Both staging scripts previously extracted MIT-marked session functions using AST
without copying the source header. The local follow-up now preserves leading
source comments and adds adaptation provenance to generated `desktop.py`.
Generated Python ASTs are unchanged. This fixes the observed local omission,
not the full distribution notice bundle or historical payloads: separate notices
might have been shipped, and those payloads were not available.
The input executable also uses the Apache-marked rvgpu header; inspect its
redistribution materials. Only generated comments were changed; runtime semantics remain unchanged.


See RECHECK.md for the current post-merge findings. New KWin build and package
code is present, but reviewed binary notices and complete source delivery remain
open. Reference text sources/hashes are in license-text-sources.json.


## Effective license reference for original WSX modules

The unmodified PolyForm Noncommercial 1.0.0 text is retained in
licenses/PolyForm-Noncommercial-1.0.0.txt, with its URL and hash recorded in
license-text-sources.json. The owner-approved grants have been effective since
2026-11-03 for the portions identified in the root LICENSE and LICENSE-MAP.md.
No additional permission or restriction was added. This grant does not apply to
third-party expression or override existing MIT, GPL, Apache or other terms.

The source and notice delivery pipeline now packages pinned component archives,
recipes, adapted source trees and notices with binaries. Collection and hashes
are evidence, not proof that all dependencies or full-image sources are complete.
Historical review notes above describe the original import limitations; use the
current effective map and delivered material receipt for the actual artifact.

Private authenticated testing is operationally approved under PRIVATE-ARTIFACTS.md.
The later owner authorization in ../private-prereleases.md permits the checked
Omarchy private Pre-release route and its publication recovery. It supersedes
that earlier document's operational ban for this route only. Neither document
adds copyright restrictions to upstream components or clears public distribution.
