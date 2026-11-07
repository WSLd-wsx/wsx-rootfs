# Private component registry migration

The two source-built graphics components were copied to the private GHCR package
`ghcr.io/wsld-wsx/wsx-rootfs-ops/graphics-components` by operations run
`42366070177`. The destination package is private and linked to the operations
repository. Original `wsx-rootfs/graphics-components` packages are retained.

| Profile | OCI digest | Original build run |
| --- | --- | --- |
| Omarchy | `sha256:25091ddb2254e82d6092fefb01a85cb570314b5645d153979001d4ddf187bb74` | 41831647428 |
| CachyOS Plasma | `sha256:1aff27b3e6ff8bd92b41aa9e708ee324890bd7ea2004ef796e59a0da0e7df288` | 41831653214 |

The migrated images retain their original OCI source, commit, run and profile
labels; their digests and image IDs were checked after read-back. Relocation is
not a rebuild or a new source origin. `components/source-delivery.json` retains
the original source pin. `components/reuse.json` selects the new private copy;
consumer admission requires the same digest and all original origin fields.
Do not delete the original package until independent retention and recovery
requirements have been reviewed. Do not claim publisher signature verification
from digest equality.

Two candidate builds and their source, component and archive checks must be
run after selecting the new registry. WSL, GPU, input and desktop acceptance
remain separate from those builds. Public source delivery and third-party license
requirements remain unchanged; license review is not completed by migration.

## Candidate build evidence

Candidate commit `a615af7f0924bec50c56d6de731d13bd96d3e7df` was exercised
by private operations runs `42366303365` (Omarchy) and `42366670850` (CachyOS).
Both read the new package by pinned digest and passed component admission,
build, offline validation and full archive verification. The reported image
SHA-256 values are `37f3b5eb0329aded3833a70f0dbd440c6c522de092e79c181ae089438b563f09`
and `114a92aeefd3cd944aec5a3e4b5be630cc20e56e2ea49bfa7f4014f7484c2569`,
respectively. The rootfs images were not retained; these hashes are runner output,
not an independently downloaded artifact.

Both jobs ultimately failed because GitHub Actions artifact storage quota was
exhausted, preventing diagnostics upload. Their complete job logs were archived
locally in the operations workspace. The first CachyOS attempt `42366308858`
failed earlier due to an upstream Arch Linux download timeout, then was retried.
No WSL boot, desktop or GPU validation was performed. These candidate builds do
not imply release or license approval, nor do they clear the quota problem.
