# WSX desktop rootfs

Build and release infrastructure for WSX desktop distributions. Implementation
is in progress. Omarchy and CachyOS graphics components have been built on
Actions; Omarchy r9/r10 rootfs candidates have passed the recorded offline and
archive checks. These checks do not establish WSL/GPU hardware acceptance.
See [source component build status](docs/component-package.md).

**Contributions:** WSX is currently in alpha and is developed independently.
External pull requests are temporarily disabled. Bug reports and testing feedback
are welcome through [Issues](https://github.com/WSLd-wsx/wsx-rootfs/issues).

Read [AGENTS.md](AGENTS.md) and the approved
[component ownership contract](docs/component-ownership.md).
[Source provenance](docs/provenance.json) includes working-tree content hashes.

Run local release-selection tests with:

```sh
python3 -m unittest discover -s tests -v
```

The image recipes, build and validation scripts run independently from this
checkout; see [local builds](docs/local-build.md). With authenticated GitHub CLI,
`python3 scripts/releases.py --version 4.0.6` resolves the exact official stable
Omarchy release and commit. CachyOS uses an explicit WSX snapshot label, not an
official upstream release version.

Operational GitHub Actions live in the private `wsx-rootfs-ops` repository;
this repository does not contain active workflow definitions. The byte-preserved
[workflow history](components/workflow-history/20261107/) is evidence for older
build receipts and does not execute. Publication follows the release protocol
and requires independently verified source and license delivery. Earlier remote
runs and hardware results do not establish the status of a newly built image.

See the [Draft testing handoff](docs/draft-testing.md) for authenticated downloads,
complete asset verification, decompression, initialization and real-machine
acceptance boundaries. The instructions do not imply that a candidate has passed
those hardware tests.

## License boundaries and source materials

Source grants are effective under the [module license map](LICENSE-MAP.md).
PolyForm Noncommercial applies only to the original independent WSX portions
identified in that map. It does not restrict the upstream system packages,
graphics components, their source archives, or GPL-covered combinations.
Original build tools and explicit original helpers use GPL-2.0-or-later;
third-party code retains its own notices and terms. The rootfs is a collection
of differently licensed components, not a wholly noncommercial work.

Each r9/r10 Release includes `component-sources.tar`, `component-materials.json`
and `component-source.json` for the paired graphics components and reconstruction
materials. `sources.json` records system-package versions. A version list is not
the complete corresponding source for those packages; that remaining delivery
gap is recorded in the [practical image review](docs/licensing/OMARCHY-IMAGE-REVIEW.md).
No new blanket license or permission is created by these source-delivery records.

New image builds use a [shared graphics source bundle](components/SOURCE-DELIVERY.md)
plus a small image-specific recipe, instead of repeating `component-sources.tar`.
Private GHCR packages and existing r9/r10 assets remain unchanged. Private source pins require authenticated access; publicly distributed schema-2
images also require independently verified publicly accessible source delivery.

See the [private artifact policy](docs/licensing/PRIVATE-ARTIFACTS.md) for the
existing compile/upload gate. Historical review documents do not override the
active license map. Repository visibility is not a finding that every upstream
distribution obligation has been fulfilled.

## Current image protocol

New Omarchy and CachyOS builds require [Guest control protocol 1.0](docs/guest-control-protocol.md).
The public endpoint, packaged profile, minimum Core version and paired Windows
runtime receipt are mandatory. Existing rootfs images are historical references,
not targets for another compatibility build. The Windows metadata pin lives in
`components/desktop-runtime`; no sibling checkout or Windows binary is needed by
image CI. Actual runtime installation and admission remain Core responsibilities.
