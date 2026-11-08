# WSX desktop rootfs

This repository contains the source inputs, recipes and validation scripts for
`wsx-omarchy` and `wsx-cachyos-plasma`. The instructions below build the paired
Linux graphics components and the rootfs **on the local machine**. The component
sources, build outputs, rootfs directory and compressed archive remain in a local
work directory. Nothing in this procedure uploads a package or creates a Release.

The local build needs network access for the pinned source archives, signed
distribution packages, builder image and release identity checks.

## Requirements

Use an x86-64 Linux machine with Docker, Git, Python 3, GitHub CLI (`gh`), GNU
`tar`, `zstd`, `/usr/bin/time`, ACL and libcap tools. The rootfs builder runs as a
privileged container and the archive verification runs as root; use an isolated
build machine. Allow substantial disk space and time for compilation, package
installation, the rootfs, the compressed archive and a full extraction. The
archive script checks for sufficient free space before compression.

The build reads the exact source and builder pins from `components/sources.json`
and `components/builder.json`. Component builds verify downloaded source hashes,
record compiler inputs and retain source and license materials. Distribution
package repositories are signed but some are rolling; recorded versions provide
traceability, not a promise of byte-identical rebuilds. Do not disable signature
checks or replace the paired private graphics stack with distribution packages.

Start from the repository root at the intended Git commit. Keep the checkout
unchanged during compilation and image assembly. `gh` must be authenticated for
release identity and deduplication checks; access to Drafts requires appropriate
repository permission. Do not put tokens into files, command history or build
logs. No private GHCR token is needed for the local source build described here.

## 1. Select a profile and prepare the build

Run the command blocks in the same Bash shell. Choose **one** profile and set a
version and a positive WSX revision. Omarchy uses an official stable upstream
Release, resolved to its commit. CachyOS uses a `YYYY.M.D` WSX snapshot label,
not an official upstream release version; its long-term naming policy is not yet
settled. The example versions are placeholders: inspect existing Releases and
choose a new revision when inputs change. Existing public assets are immutable.

```sh
set -e
set -o pipefail

# Omarchy example:
PROFILE=omarchy
VERSION=4.0.6
REVISION=15

# Alternatively, for CachyOS Plasma:
# PROFILE=cachyos-plasma
# SNAPSHOT=2026.11.8
# REVISION=1

REPO=WSLd-wsx/wsx-rootfs
mkdir -p out
WORK=$(mktemp -d "$PWD/out/local-rootfs.XXXXXXXX")
printf 'Local build directory: %s\n' "$WORK"

python3 scripts/check-provenance.py
python3 scripts/desktop_contract.py --check-pin
python3 -m unittest discover -s tests -v

if [ "$PROFILE" = omarchy ]; then
  python3 scripts/prepare-build.py --version "$VERSION" --revision "$REVISION" \
    --repo "$REPO" --output "$WORK/build.json"
elif [ "$PROFILE" = cachyos-plasma ]; then
  python3 scripts/prepare-cachyos.py --snapshot "$SNAPSHOT" --revision "$REVISION" \
    --repo "$REPO" --output "$WORK/build.json"
else
  echo 'Unsupported profile' >&2; false
fi
python3 -c 'import json,sys; sys.exit("Completed image already exists; inspect its release") if json.load(open(sys.argv[1]))["completed"] else None' "$WORK/build.json"
```

The prepare command checks existing release identities. If a completed matching
image exists, the final command stops. A conflicting or existing prerelease
version is rejected; select another revision. Missing source inputs or a failed
compatibility check must be fixed rather than bypassed.

## 2. Build the graphics components locally

The profile-specific scripts compile Mesa/Zink and Venus, plus
Hyprland/Aquamarine for Omarchy or KWin for CachyOS. They assemble the paired
runtime and collect the source and notices.
The downloaded upstream inputs are verified against their pinned SHA-256 hashes.

```sh
IMAGE=$(python3 -c 'import json; print(json.load(open("components/builder.json"))["image"])')
python3 scripts/watch-component-build.py "$WORK/component-build" -- \
  docker run --rm -e PYTHONUNBUFFERED=1 \
    -v "$PWD:/workspace:ro" -v "$WORK:/output" "$IMAGE" \
    bash "/workspace/distros/$PROFILE/build-components.sh"
```

On success, `$WORK/source-archives/` contains the downloaded source inputs,
`$WORK/component-build/` contains the build trees, logs and compilation receipt,
`$WORK/private/` contains the assembled runtime, and
`$WORK/component-materials/` contains the paired source and notice materials.
Keep these together with `$WORK/component-source.json`; they are the evidence
for these specific local binaries. Build completion does not establish GPU or
hardware acceptance.

To also retain a portable local component package and its checksums, run:

```sh
sudo /usr/bin/python3 scripts/package-source-components.py "$WORK" "$WORK/packages"
```

This writes the package only to `$WORK/packages/`. It does not publish it.

## 3. Assemble the local rootfs

Create the image-specific source snapshot from the local component receipt, then
run the profile's rootfs recipe in the pinned builder. The snapshot preserves
the distinction between component compilation and image assembly.

```sh
PYTHONPATH=scripts python3 -c 'import sys; from pathlib import Path; from image_materials import image_snapshot; image_snapshot(Path.cwd(), Path(sys.argv[1]))' "$WORK"
BUILDER="wsx-local-$(basename "$WORK")"
docker run -d --name "$BUILDER" --privileged \
  -v "$PWD:/workspace:ro" -v "$WORK:/output" "$IMAGE" sleep infinity

if [ "$PROFILE" = omarchy ]; then
  docker exec "$BUILDER" bash /workspace/distros/omarchy/bootstrap-rootfs.sh
  docker exec "$BUILDER" bash /workspace/distros/omarchy/build-rootfs.sh
else
  docker exec "$BUILDER" bash /workspace/distros/cachyos-plasma/bootstrap-rootfs.sh
  docker exec "$BUILDER" bash /workspace/distros/cachyos-plasma/configure-rootfs.sh
fi

docker stop "$BUILDER"
docker rm "$BUILDER"
```

The profile scripts install the desktop packages, stage the locally built
runtime and Guest protocol endpoint, sanitize the image, and run offline
validation. The resulting filesystem is `$WORK/rootfs/`; validation reports and
package inventories are written alongside it in `$WORK/`. Stop on any failure.
If a container step fails, preserve the work directory and diagnostics, then
stop and remove only the container identified by `$BUILDER`.

## 4. Create and verify the local rootfs archive

Use the repository archive tool directly for this local build. It checks image
hygiene, compresses the filesystem, tests the zstd stream, fully extracts it,
and compares file contents and metadata including ownership, links, ACLs, xattrs
and capabilities. This requires root so metadata can be restored and verified.

```sh
ARCHIVE="$WORK/wsx-$PROFILE-local-x86_64.rootfs.tar.zst"
sudo /usr/bin/python3 scripts/archive.py "$WORK/rootfs" "$ARCHIVE"
sha256sum "$ARCHIVE" | tee "$WORK/rootfs.sha256"
printf 'Local rootfs archive: %s\n' "$ARCHIVE"
```

The archive and a `*.report.json` compression and verification report remain in
`$WORK/`. The report records compression size, time, peak memory and the checks
actually performed. No WSL distribution is imported or started by these steps.

This local archive is a **build artifact**, not a complete publishable WSX
Release: it does not include a Release manifest, completion marker or uploaded
source assets. In particular, `finalize.py` and `finalize-cachyos.py` require the
component receipt to match the configured published shared source Release. A
fresh local component build has its own receipt and cannot simply reuse the
existing public source pin. For release publication, first establish matching
source delivery and follow the [release protocol](docs/release-protocol.md); do
not fabricate a receipt or weaken source verification.

## Validation and ownership

Offline checks and archive extraction do not prove WSL boot, GPU first frame,
desktop functionality or sustained stability. Record those stages separately
when tested on real hardware; see [build evidence](docs/build-evidence.md) and
the [testing handoff](docs/draft-testing.md).

The rootfs contains the Guest control protocol, desktop session adapters and
paired user-space graphics components. wsx-core owns the Windows host, rootfs
download/import, and kernel module selection; see the
[component ownership contract](docs/component-ownership.md) and
[Guest control protocol](docs/guest-control-protocol.md).

Source materials and license boundaries are documented in
[LICENSE-MAP.md](LICENSE-MAP.md) and [components/SOURCE-DELIVERY.md](components/SOURCE-DELIVERY.md).
Individual third-party terms remain in force; source and license evidence is not
itself a finding that every distribution obligation has been fulfilled.

WSX is in alpha. External pull requests are temporarily disabled; bug reports and
testing feedback are welcome through [Issues](https://github.com/WSLd-wsx/wsx-rootfs/issues).
