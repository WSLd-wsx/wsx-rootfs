# Private Omarchy test delivery

The owner approved private Pre-release delivery for Omarchy rootfs on 2026-11-03.
This supersedes the earlier operational prohibition on Release publication in
`licensing/PRIVATE-ARTIFACTS.md` for this specific route only. Existing component
source-license inputs stay unchanged so the verified component package remains
reusable. This is a storage/publication decision, not a new copyright grant.

The repository must remain private. The existing private rootfs gate, complete
source asset set, hashes and offline checks remain mandatory. Uploads start as a
Draft; every payload asset and completion marker is downloaded and verified before
the release becomes a Pre-release with `latest=false`. Partial uploads remain
Draft. Existing published assets are never overwritten; changed inputs require
a new WSX revision. Normal stable image resolution excludes Pre-releases.

No public repository, stable promotion or hardware acceptance is authorized.
Prerelease status does not waive upstream license obligations. Components remain
in private GHCR; rootfs files are available as authenticated Release downloads.
Optional Actions diagnostics can fail without invalidating the verified payload.
