# Guest protocol 1.0 image rebuild

The user authorized two public test Pre-releases, without stable promotion or
replacement of existing installations. Omarchy uses image build commit
`8040feaab8df05cbd803215d8261364575236630`. The CachyOS rebuild uses
`2281d078de4b3bc60b2fa143e511a9a52c97194b`. New images require Core 0.2.1,
Guest control protocol 1.0 and the declared Native runtime pairing. An older
image is not the compatibility target for this rebuild.

## Checks and failure history

[Contract CI 42032053704](https://github.com/WSLd-wsx/wsx-rootfs/actions/runs/42032053704)
passed all 204 tests, including privileged tar/zstd metadata checks. Local tests
passed 192 and skipped 12 requiring unavailable tools or privileges.

The first image attempts, [Omarchy 42030975189](https://github.com/WSLd-wsx/wsx-rootfs/actions/runs/42030975189)
and [CachyOS 42030986050](https://github.com/WSLd-wsx/wsx-rootfs/actions/runs/42030986050),
failed before image assembly because the original graphics component Actions run
records returned HTTP 404. The immutable registry packages and published source
indexes remained available. Commit `8040fea` binds registry reuse to their fixed
OCI digest, repository/commit/run/profile labels and exact published source
receipt. It preserves package/source byte validation. It does not represent an
unavailable Actions run as a currently successful run.

Current image assembly inputs and notices are recorded separately from the
original component compilation receipt. Reusing compiled graphics components
neither fabricates a new compilation nor changes their license terms.

## Omarchy 4.0.6-r12

[Build 42032163596](https://github.com/WSLd-wsx/wsx-rootfs/actions/runs/42032163596)
completed successfully and published [the public Pre-release](https://github.com/WSLd-wsx/wsx-rootfs/releases/tag/wsx-omarchy-4.0.6-r12).

- Archive size: 1,397,893,691 bytes.
- Archive SHA-256: `8ed1f22e3d28c51454900bd7aceaf71095867d2842b35496ac7915cc7af7aac3`.
- Full archive verification: 128,694 metadata entries; zstd stream, file hashes,
  UID/GID, mode, symlinks, hardlinks, ACLs, xattrs and capabilities passed.
- The packaged `/usr/bin/wsx-guest host-call` endpoint answered a protocol 1.0
  capability request inside an offline chroot. No systemd session or GPU ran.
- The publisher read back and hashed all uploaded assets before publishing the
  completion marker. A separate local check fetched public metadata bytes and
  compared the complete asset set, sizes and GitHub digests against completion.

## CachyOS 2026.11.5-r1 publication recovery

[Build 42032175283](https://github.com/WSLd-wsx/wsx-rootfs/actions/runs/42032175283)
passed image assembly, Guest offline checks, full archive verification and the
candidate/source gate. After uploading the assets, the publication readback
failed with an HTTP/2 `PROTOCOL_ERROR` for the rootfs asset. The original archive
SHA-256 is `d8ab06d9efd3031ae2fbff95120e478e9be6433df0302e8d6e80091b96451fc9`.
This run did not establish completed public publication.

The manual `recover-public-candidate.yml` workflow requires the original run ID,
exact Draft tag and archive hash. It checks the original successful validation
steps, repository, workflow, main branch, commit, asset set and every downloaded
asset's server digest. The normal publisher then repeats its full payload/source
checks, compares existing bytes and only then completes the original Draft. It
never overwrites an attachment or rebuilds an image. Failed HTTP reads retry at
most three times and discard partial responses. Recovery run [42035669086](https://github.com/WSLd-wsx/wsx-rootfs/actions/runs/42035669086)
rejected the missing Draft without mutation. The user confirmed manually deleting
that Draft. Its rootfs asset also returned HTTP 404. Recovery did not succeed;
rebuild [42036204244](https://github.com/WSLd-wsx/wsx-rootfs/actions/runs/42036204244)
was dispatched with bounded download retries. The publisher also rechecks the
original Draft ID before recovery mutations, rejecting deletion or replacement
between initial admission and publication. The rebuild completed successfully and published
[the public Pre-release](https://github.com/WSLd-wsx/wsx-rootfs/releases/tag/wsx-cachyos-plasma-2026.11.5-r1).
The deleted attempt is retained only as failure evidence; its digest is not the
published image digest.

- Published archive size: 2,030,647,719 bytes.
- Published archive SHA-256: `f57865aa158671faa18280e650ea25bdfb79f0f878309ec8fa2d99e026499ed0`.
- Full archive verification: 245,109 metadata entries; zstd stream,
  file hashes, UID/GID, mode, symlinks, hardlinks, ACLs, xattrs and capabilities passed.
- The packaged Guest protocol endpoint answered the same offline protocol 1.0
  capability request. WSL and GPU were not started by the builder.
- Publication read back and verified all attachments. Independent public metadata
  downloads, completion/manifest/source consistency and all GitHub asset digests
  also passed locally.

[Final recovery checks 42037833543](https://github.com/WSLd-wsx/wsx-rootfs/actions/runs/42037833543)
passed all 212 tests, with no skips. Local execution passed 200 and skipped 12
requiring unavailable tools or privileges. These tests include partial-download
retry, exact original build admission and deletion/replacement rejection; they
are not new-image hardware tests.

## Build commands

```sh
gh workflow run omarchy.yml --repo WSLd-wsx/wsx-rootfs --ref main -f test_only=false -f upstream_version=4.0.6 -f revision=12 -f debug_enabled=false
gh workflow run cachyos-plasma.yml --repo WSLd-wsx/wsx-rootfs --ref main -f test_only=false -f snapshot=2026.11.5 -f revision=1
```

## Acceptance boundary

Both declarations pair with runtime receipt SHA-256
`617965791e6928e535a47ccff46b63983455e5f9dbcc581446776d3654841a10`.
This is a compatibility declaration, not proof of new-image graphics acceptance
or a public Windows runtime package. Core must still validate the actual runtime
files before use.

Build/offline validation and publication are separate from WSL boot, account
initialization, GPU first frame, input, display adaptation, normal retirement,
restart and sustained stability. The new-image hardware stages remain `not_run`;
previous Omarchy/CachyOS desktop results do not transfer to these new bytes.
No existing distro, virtual disk or running desktop was modified by this build.

Local logs and downloaded metadata are retained under
`out/protocol-rebuild-20261105-01/` (ignored build evidence). Public manifest,
sources, validation and completion assets are the durable image evidence; Actions
log retention is not guaranteed.
