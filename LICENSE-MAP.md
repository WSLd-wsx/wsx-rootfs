# Effective module license map

Updated 2026-11-16 by owner direction. Read LICENSE for the current grants.
These rules cover only expression the licensor has authority to license;
third-party statements and copied expression retain their applicable rights.
More specific exceptions below take priority over directory defaults.

| Paths | License / treatment |
| --- | --- |
| `guest/**`, `tests/**`, original `docs/**`, `README.md`, `AGENTS.md`, `.gitignore`, `.gitattributes` | Apache-2.0 for owner-original expression; existing grants and upstream notices remain in force |
| `scripts/**`, `.github/**`, `components/**`, `schema/**`, `distros/**` except imported upstream material | Apache-2.0 for owner-original expression |
| `LICENSE`, `LICENSE-MAP.md`, `docs/provenance.json`, `docs/licensing/{modules,rules,license-text-sources}.json`, `docs/licensing/{LICENSE-MAP,OUTPUT-LICENSES,PRIVATE-ARTIFACTS}.md` | Apache-2.0 for original mapping/prose; referenced license texts are unchanged |
| `docs/licensing/licenses/**` | Each text's own terms; no PolyForm overlay |
| Imported helpers listed below | Apache-2.0 for owner-original expression; preserve prior grants and upstream notices |
| Existing MIT-marked files listed by `existing-mit` in `docs/licensing/rules.json` | Retain MIT notices, including MIT additions in `linear-depth-segregation.patch` |
| `vendor/wsx-guest-sources/guest-opaque/kwin-opaque-consumer.patch` | Retain upstream GPL-2.0-or-later; original WSX additions GPL-2.0-or-later |
| Other `vendor/wsx-guest-sources/**/*.patch` | Retain upstream context and existing notices; owner-original additions without another existing applicable grant are MIT under `docs/licensing/licenses/WSX-MIT.txt` |
| `vendor/rvgpu/include/librvgpu/rvgpu-protocol.h` | Apache-2.0; retain Panasonic notices |
| `distros/cachyos-plasma/upstream/pacstrap.conf` | CC0-1.0 |
| `distros/cachyos-plasma/upstream/source.json` | Apache-2.0 for the owner-original index, not indexed upstream material |
| `distros/cachyos-plasma/upstream/{iso-cachyos-release,iso-os-release}` | Retained upstream GPL-3.0-only; pinned root LICENSE and source mapping in `upstream/source.json`; no PolyForm restriction |

Imported original helper paths, relative to `vendor/wsx-guest-sources/`:

- `guest-compat/build.py`, `guest-compat/build-venus.py`
- `guest-opaque/build-compositor.py`, `guest-opaque/prepare-kwin.py`
- `network/install.py`, `network/README.md`, `network/manifest.json`,
  `network/omarchy-4.0.6/manifest.json`
- `session/enter.py`, `session/install.py`, `session/wsx-launch-app`, `session/README.md`
- `device-host/production/test-plasma-session.py`

Existing file notices prevail over defaults. A new imported file is not implicitly
original or cleared; add an explicit exception before external distribution.
Facts, names and source indices do not grant rights in referenced works.

`docs/licensing/modules.json` and `rules.json` implement these boundaries;
`inventory.json` records current file hashes and prior evidence classifications.
Its historical `conditional-future-license` category describes the evidence class,
not an inactive grant: current treatment comes from this map and modules.json.
The approved pre-implementation snapshot in `activation-scope.json` is historical
scope evidence, not a competing current map.

See [generated output exceptions](docs/licensing/OUTPUT-LICENSES.md),
[third-party notices](docs/licensing/THIRD-PARTY-NOTICES.md), and
[private artifact policy](docs/licensing/PRIVATE-ARTIFACTS.md).

`guest/protocol-retirement.py` retains MIT from the verified wsld Native retirement helper; this narrow imported exception overrides the `guest/**` default.

The instance-labelled Guest input adapter `guest/input.c` derives from the retained MIT `vendor/wsx-guest-sources/input/guest.c`; its linked protocol header retains its Apache-2.0 notice. The owner-original Guest device-view helper is Apache-2.0; prior GPL grants remain valid.
