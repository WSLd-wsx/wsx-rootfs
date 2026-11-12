# Explicit source and generated-output grants

Effective 2026-11-03; these are component boundaries, not additions to PolyForm.
The GPL grant on a generator does not automatically license its output.

| Source expression / output | Treatment |
| --- | --- |
| `scripts/stage-guest.py`: original literal/replacement expressions inserted into `usr/lib/wsx/runtime/desktop.py` | MIT; original copied adapter notices retained |
| `scripts/stage-cachyos.py`: original literal/replacement expressions returned by `session_source()` and written as `desktop.py` | MIT; original copied adapter notices retained |
| `scripts/stage-guest.py`: original session installer adaptation | GPL-2.0-or-later |
| `scripts/stage-cachyos.py`: original literal/replacement expressions returned by `guest_source()` | PolyForm-Noncommercial-1.0.0, as is original `guest/wsx-guest.py` |
| `scripts/stage-cachyos.py`: original `initialize-user.sh` shell template in `main()` | PolyForm-Noncommercial-1.0.0 |
| Remaining staging tool logic | GPL-2.0-or-later |
| Original `guest/` files copied into the image | PolyForm-Noncommercial-1.0.0 |
| Imported original `session/` and `network/` helpers/adaptations | GPL-2.0-or-later; upstream patch context separate |
| `scripts/session_venus_policy.py`: modifications to staged session helpers | GPL-2.0-or-later; original copied notices retained |
| Private KWin combined binaries/source | Applicable GPL, with original per-file MIT and GPL notices preserved |
| Mesa/Venus and Hyprland/Aquamarine outputs | Exact upstream/dependency terms and retained adapter notices; not PolyForm or automatically GPL |
| Input adapter binary | Applicable MIT source and Apache-2.0 header terms |

The MIT grant for the named original expressions is in `licenses/WSX-MIT.txt`.
The PolyForm standard and Required Notice are in the root LICENSE and the retained
license text. These exceptions apply to the identified embedded expressions in
source form as well as in generated files. They do not relicense upstream code.

`MODULE-LICENSES.json`, `MODULE-NOTICES.txt`, license texts and original notices
are shipped with component sources and installed in the image. `IMAGE-LICENSES.json`
binds installed outputs and package evidence. Symlinks, file hashes and generated
metadata do not change the target software's rights or establish image clearance.
