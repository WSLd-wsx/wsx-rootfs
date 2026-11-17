# Private workflow testing while licensing remains pending

The user designates the individual WGY (GitHub: wgy-wsx) <wgy@wsxdesk.com>
as the public rightsholder for eligible original work. The legal name is not
public. Candidate source-available terms are not effective. Existing third-party declarations and
rights remain unchanged; this testing restriction is a project publication policy,
not a replacement license imposed on third-party software.

The owner attests that the newly imported KWin builder, component packaging and
consumption scripts, and CachyOS recipes are original work or adaptations of their
own WSX work, with no added third-party code except the existing vendor material.
This is an owner statement, not independent proof of every upstream relationship.

Manual component, Omarchy and CachyOS workflows default to `test_only: true`.
Compilation, assembly and offline checks run normally. Binary candidate uploads,
rootfs payload transfers, Draft creation and retries are disabled in that mode.
Source materials and diagnostics can be uploaded to this private repository.
Scheduled Omarchy runs also use test-only mode. Disabling the input does not grant
publication permission: the mandatory licensing gate still rejects publication.

Component builds retain pinned source archives, recipe files, adapted/patched
build materials, selected generated definitions, package/toolchain listings and
notice candidates. Component packages bind source and notice hashes to the runtime
receipt; consumers verify them. Both distro recipes install collected original
notices under `/usr/share/licenses/wsx-components`.

Collection completion is not complete corresponding source or legal clearance.
Non-vendored dependency sources, image-wide package/media/font/trademark review,
rights confirmation and publication approval remain open. The owner selected
unmodified PolyForm Noncommercial for eligible independent modules; no separate
source-only redistribution restriction or enterprise-evaluation addendum applies
to that proposed grant. KWin combinations
must retain applicable GPL obligations. No universal noncommercial restriction can
be imposed on the complete rootfs. Local and CI checks are not hardware acceptance.

`audit-licenses.py --check` compares file coverage, bytes, rules and source evidence.
The recorded HEAD and per-file commit lists are historical snapshot metadata; a
commit alone does not invalidate unchanged file evidence. Regeneration refreshes
that history. `--require-release-ready` continues to fail independently of hashes.


The practical stopping rule in MODULES.md bounds further audit work. Existing
private compilation and offline validation may proceed while candidate grants
remain inactive. Do not treat an inactive grant as a compiler failure, and do
not bypass the publication gate merely because integrity checks pass. Further
review should be driven by concrete build outputs and identified omissions,
not by a requirement to eliminate every hypothetical uncertainty.
