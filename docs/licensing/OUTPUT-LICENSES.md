# Explicit source and generated-output grants

Updated 2026-11-16; these are component boundaries and preserve prior grants.
A license grant on a generator does not automatically license its output.

| Source expression / output | Treatment |
| --- | --- |
| `scripts/stage-guest.py`: original literal/replacement expressions inserted into `usr/lib/wsx/runtime/desktop.py` | MIT; original copied adapter notices retained |
| `scripts/stage-cachyos.py`: original literal/replacement expressions returned by `session_source()` and written as `desktop.py` | MIT; original copied adapter notices retained |
| `scripts/stage-guest.py`: original session installer adaptation | Apache-2.0 for owner-original expression; earlier grants retained |
| `scripts/stage-cachyos.py`: original literal/replacement expressions returned by `guest_source()` | Apache-2.0 for owner-original expression, with earlier grants retained |
| `scripts/stage-cachyos.py`: original `initialize-user.sh` shell template in `main()` | Apache-2.0 for owner-original expression; earlier grants retained |
| Remaining staging tool logic | Apache-2.0 for owner-original expression; earlier grants retained |
| Original `guest/` files copied into the image | Apache-2.0 for owner-original expression, with existing grants retained |
| Imported original `session/` and `network/` helpers/adaptations | Apache-2.0 for owner-original expression; upstream patch context and prior grants retained |
| Private KWin combined binaries/source | Applicable GPL, with original per-file MIT and GPL notices preserved |
| Mesa/Venus and Hyprland/Aquamarine outputs | Exact upstream/dependency terms and retained adapter notices; not PolyForm or automatically GPL |
| Input adapter binary | Applicable MIT source and Apache-2.0 header terms |

The MIT grant for the named original expressions is in `licenses/WSX-MIT.txt`.
The Apache-2.0 grant and retained license text are identified in the root LICENSE.
Earlier applicable grants remain intact. These exceptions apply to embedded expressions in
source form as well as in generated files. They do not relicense upstream code.

`MODULE-LICENSES.json`, `MODULE-NOTICES.txt`, license texts and original notices
are shipped with component sources and installed in the image. `IMAGE-LICENSES.json`
binds installed outputs and package evidence. Symlinks, file hashes and generated
metadata do not change the target software's rights or establish image clearance.
