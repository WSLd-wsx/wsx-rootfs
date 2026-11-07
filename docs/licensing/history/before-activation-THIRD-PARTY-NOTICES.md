# Third-party notices — review draft, incomplete for distribution

Existing file notices remain authoritative and unchanged. This index neither
relicenses materials nor establishes that a recipient previously received a
grant. See `inventory.json` for exact file hashes and notice locations.

- `vendor/rvgpu/include/librvgpu/rvgpu-protocol.h`: Apache-2.0;
  Copyright (c) 2022 Panasonic Automotive Systems, Co., Ltd. Preserve the header.
  An unmodified [official Apache text](https://www.apache.org/licenses/LICENSE-2.0.txt)
  is stored in `licenses/Apache-2.0.txt`. Its hash is in the inventory. Original
  upstream NOTICE availability and changed-file attribution remain to be checked.
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
  licenses/CC0-1.0.txt. Other imported CachyOS configuration/identity
  files require source-era license evidence. No right to trademarks is inferred.

The repository contains no Cargo manifest or npm package manifest. The file
`components/package.json` is an OCI/archive pin, not npm licensing metadata.
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


## Selected license reference for original WSX modules

The official unmodified PolyForm Noncommercial 1.0.0 text is retained as a selected
candidate reference in licenses/PolyForm-Noncommercial-1.0.0.txt, with its URL and
hash in license-text-sources.json. It is not a blanket notice or grant over any
third-party module. The owner selected no additional permission or restriction;
the previous custom-policy draft is historical and superseded. This preparation
does not activate the candidate or replace any existing notice above.
