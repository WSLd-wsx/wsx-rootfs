# Module license activation proposal

Status: APPROVED by the owner on 2026-11-03. Implemented grants and policy are
in the root LICENSE, LICENSE-MAP.md and PRIVATE-ARTIFACTS.md. This document records
the approved proposal, not a second competing grant. The exact current paths and SHA-256 values are in
`activation-scope.json`; this is a scope snapshot, not a new license text.

## One approval, four decisions

1. Activate the grants below for the approved current tree and subsequent
   contributions the owner has authority to license. Licensor: the individual
   **WGY (GitHub: wgy-wsx) <wgy@wsxdesk.com>**. Do not infer a company or transfer
   of third-party rights. Apply the unmodified standard texts.
2. Expressly license the owner's original imported helpers and staging additions
   as listed below, relying on the owner's existing independent-authorship
   attestation. Any known copied third-party expression remains excluded.
3. Permit authenticated binary component and rootfs test artifacts in this private
   repository for the owner's testing and component reuse, with paired sources and
   notices. Do not authorize public promotion or external distribution of images.
4. After implementation and checks, prepare a new root commit containing effective
   licenses. Preserve the old history and current files. Show exact old/new refs
   and obtain the previously required concrete rewrite confirmation before using
   an explicit force lease. Do not reset history while grants are still drafts.

## Directory rules (exceptions take priority)

| Paths | Effective treatment after approval |
| --- | --- |
| `guest/`, `tests/`, original `docs/`, `README.md`, `AGENTS.md`, `.gitignore`, `.gitattributes` | PolyForm Noncommercial 1.0.0, verbatim, for owner-original expression |
| `scripts/`, `.github/`, `components/`, `schema/`, `distros/` except imported `upstream/` material | GPL-2.0-or-later for owner-original tools, recipes, workflow code and metadata |
| `docs/provenance.json`, `docs/licensing/{modules,rules,license-text-sources}.json` and new operative license maps | GPL-2.0-or-later for owner-original expressive content needed for reconstruction |
| `docs/licensing/licenses/**` | Retain each reference/license text and original notice; no PolyForm overlay |
| The explicit imported helper list below | GPL-2.0-or-later for owner-original expression; preserve any existing third-party terms |
| The 12 existing MIT-marked paths in `rules.json` rule `existing-mit` | Retain MIT declarations, including MIT additions in the Mesa patch; no PolyForm overlay |
| `vendor/wsx-proto/guest-opaque/kwin-opaque-consumer.patch` | Retain GPL-2.0-or-later context; license owner-original patch contributions compatibly under GPL-2.0-or-later |
| Other `vendor/wsx-proto/**/*.patch` | Preserve upstream context and exact existing notices; offer owner-original additions under MIT where no existing applicable grant is present; no claim to upstream expression |
| `vendor/rvgpu/include/librvgpu/rvgpu-protocol.h` | Retain Apache-2.0 and Panasonic notices |
| `distros/cachyos-plasma/upstream/pacstrap.conf` | Retain CC0-1.0 |
| `distros/cachyos-plasma/upstream/source.json` | GPL-2.0-or-later for the original source index only |
| `distros/cachyos-plasma/upstream/{iso-cachyos-release,iso-os-release,netinstall.yaml}` | No WSX grant; exact source-era permission remains to be established |

The directory GPL choice is deliberate, not a claim that invoking a GPL program
makes every independent tool GPL. It simplifies reconstruction and permits others
to use those GPL tools commercially under their terms. Source indices do not
license the software they describe. Repository prose quoting third parties and
upstream-derived fragments retain their original rights.

Explicit imported helper paths (relative to `vendor/wsx-proto/`):

- `guest-compat/build.py`, `guest-compat/build-venus.py`
- `guest-opaque/build-compositor.py`, `guest-opaque/prepare-kwin.py`
- `network/install.py`, `network/README.md`, `network/manifest.json`,
  `network/omarchy-4.0.6/manifest.json`
- `session/enter.py`, `session/install.py`, `session/wsx-launch-app`, `session/README.md`
- `device-host/production/test-plasma-session.py`

## Generated and compiled outputs

- Private KWin combined binaries and corresponding source: applicable GPL terms,
  with original per-file MIT notices retained; never PolyForm.
- Mesa/Venus and Hyprland/Aquamarine outputs: their actual upstream and dependency
  terms, with retained adapter notices; never inferred to be GPL merely because
  their build scripts are GPL.
- `usr/lib/wsx/runtime/desktop.py`: retain the source adapter's MIT notice and
  expressly grant MIT for owner-original expressions inserted by either staging
  script. Identify these embedded template/replacement portions as an explicit
  MIT exception in the scripts; the rest of each script remains GPL.
- `usr/bin/wsx-guest` and `usr/lib/wsx/initialize-user.sh`: PolyForm for original
  Guest code and expressly identified original generated additions/templates.
  Mark those embedded expressions as PolyForm exceptions in the staging script.
- Copied/adapted `session/` and `network/` helpers: applicable GPL helper grant,
  including original staging adaptations, with upstream patch contexts excluded.
- Symlinks and metadata do not change the target software's license. A complete
  rootfs has multiple licenses; the owner cannot prohibit all commercial use of it.

## Concrete implementation and gates

Add a root `LICENSE` explaining the module rules, operative `LICENSE-MAP.md`,
verbatim standard texts and the owner's Required Notice for PolyForm scope. Update
machine rules and output notices to active grants; remove conflicting draft-only
statements from operative files while retaining dated historical evidence.
No original upstream notice is removed. Manual per-file headers are not required
except the small embedded-expression exceptions described above.

Separate source-license activation, private artifact permission and public image
readiness. Replace unconditional refusal with concrete checks: module coverage,
retained notices, paired source/build materials, integrity, profile compatibility,
and unresolved material actually included in a proposed external payload.
Unknown CachyOS upstream rights do not prevent activating independent WSX grants
or owner-controlled private component tests; they still prevent claiming that an
external payload containing them is cleared, including source bundles.

Keep `test_only=true` as compile-only diagnostics. After this approval,
`test_only=false` may retain private authenticated test binaries and paired source
materials. Guard repository privacy and preserve separate authorization for public
releases; this proposal does not activate a public publishing workflow.

After implementation checks pass, prepare and confirm the history rewrite so the
new root commit contains effective source licenses and the revised workflows.
Then build Omarchy components from that commit, select the actual artifact/hash
in `components/reuse.json` through a normal follow-up commit, and let rootfs reuse
it. Runs from an older draft-license commit are diagnostic evidence, not the
selected final package. Pinning a real package necessarily happens after its
source commit exists; do not invent a future artifact or create a circular pin.

## Commercial scope

The standard PolyForm permitted purposes, distribution, patent and remedy terms
apply unchanged. No special 30-day enterprise trial or additional restriction is
added. Its express permissions for listed noncommercial organizations remain.
Commercial use outside the grant requires a separate applicable permission for
PolyForm-covered original code. MIT/GPL/BSD/Apache rights remain available under
those licenses, including commercial rights. This proposal does not promise to
prevent independent reimplementation or all competing products.

Official texts:
- https://polyformproject.org/licenses/noncommercial/1.0.0.txt
- https://www.gnu.org/licenses/old-licenses/gpl-2.0.txt
