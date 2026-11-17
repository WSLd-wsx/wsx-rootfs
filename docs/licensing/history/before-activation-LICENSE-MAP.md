# License map — inactive review draft

This document grants no rights and changes no existing license. No root license
is activated. The designated public rightsholder for eligible original WSX work is
WGY (GitHub: wgy-wsx) <wgy@wsxdesk.com>; third-party holders are unchanged. `rules.json` classifies review work, not legal ownership. Preserve
existing declarations even where the history of effective grants is unknown.
Noncommercial restrictions would make selected future code source-available,
not OSI open source. They cannot restrict the entire rootfs or revoke prior rights.

| Boundary | Review treatment | Conditions before any future grant |
| --- | --- | --- |
| `scripts/`, `tests/`, `guest/`, `.github/`, `schema/` | Conditional independent implementation candidates | Confirm title and contributions; exclude extracted/imported code and generated derivatives |
| `distros/` excluding `upstream/` | Conditional recipes/configuration | Check reference-derived expression, upstream assets and embedded shell/config templates |
| `docs/`, `components/`, root documentation/configuration | Conditional original prose and metadata | Facts and indexed third-party material are not owned by association |
| Existing MIT files in exact rule `existing-mit` | Retain MIT declarations | No unilateral reclassification; establish grants and ownership separately |
| `vendor/**/*.patch` | Retain upstream terms and context | Determine per-file upstream terms and combination obligations; no directory-wide restriction |
| Other `vendor/wsx-proto/` helpers | Evidence insufficient for new license | Imported provenance alone does not prove authority |
| `vendor/rvgpu/` | Retain Apache-2.0 and Panasonic notices | Check original NOTICE and change attribution |
| `distros/cachyos-plasma/upstream/pacstrap.conf` | Retain CC0-1.0 | Preserve dedication |
| Other imported `upstream/` files | Evidence insufficient, except local source index | Obtain exact source-era terms and trademark review |
| `licenses/PolyForm-Noncommercial-1.0.0.txt` here | Unmodified selected candidate reference | No grant until eligible scope/version activation is approved; no addendum |
| `licenses/Apache-2.0.txt` here | Official license copy | Supplements existing header; not a grant for WSX code |

The machine rules use explicit priority; equal-priority matches fail, uncovered
paths fail, and indexed source hash mismatches fail. Each generated inventory
entry includes a hash, category, basis, limitation, next action, local history,
source index and textual observations. Observations distinguish added patch
lines, removed lines, context and mentions; they are not legal conclusions.

Run `python3 scripts/audit-licenses.py` after changes, then review the diff and
run `python3 scripts/audit-licenses.py --check`. The inventory excludes itself
because self-hashing cannot converge. Ignored build outputs and remote payloads
are outside this repository-source inventory. The explicit
`--require-release-ready` mode fails while review blockers remain. The source migration wires this readiness mode into candidate transfer, Draft
publication and retry workflows. The low-level publisher remains a protocol tool;
its direct invocation is not a substitute for readiness review.

## Module plan

See MODULES.md and modules.json for the proposed module boundaries. Unmodified PolyForm
Noncommercial 1.0.0 is selected only for eligible independent WSX expression,
without an evaluation addendum.
Per-file upstream notices remain authoritative; module membership grants no rights.
Required GPL build materials are separately reviewed, not covered by a blanket
PolyForm default. The previous custom terms are superseded historical text, not an addendum.
The official PolyForm reference copy is not itself an effective repository grant.
