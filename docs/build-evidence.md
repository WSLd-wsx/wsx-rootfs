# Build evidence

The [Guest protocol 1.0 rebuild record](protocol-rebuild-20261105.md) covers the
completed Omarchy r12 and CachyOS 2026.11.5-r1 public Pre-releases, their exact
archive hashes, failure history and separate hardware acceptance boundary.

These records describe bounded observations, not product defaults or hardware
acceptance. Failures remain available in their original Actions runs.

| Commit | Run | Observation |
| --- | --- | --- |
| b97317620432d4fa361f96dd6369b312b21127ea | [41190933089](https://github.com/WSLd-wsx/wsx-rootfs/actions/runs/41190933089) | Contract tests and official stable release resolution passed |
| 4a81a434cbef48df7c73545dbe5a0a3216b578a1 | [41191111985](https://github.com/WSLd-wsx/wsx-rootfs/actions/runs/41191111985) | All 16 tests passed, including privileged real tar/zstd metadata extraction; no skipped tests on CI |
| 8c3dd8a4d9722055d2a7541d652741b6693a2959 | [41191549574](https://github.com/WSLd-wsx/wsx-rootfs/actions/runs/41191549574) | Failed before compilation: Arch packages libseat/libeis do not exist; corrected to seatd/libei |
| 45b2dce4ef8aa06c25bcfe9d0fab6cac36510d88 | [41191694754](https://github.com/WSLd-wsx/wsx-rootfs/actions/runs/41191694754) | Mesa/Zink, Venus and Aquamarine compiled; Hyprland configuration failed on missing hyprwire; no complete component closure |
| 4865a3e47526276265b742cb0773e93656ec1bf8 | [41192284331](https://github.com/WSLd-wsx/wsx-rootfs/actions/runs/41192284331) | Rootfs workflow failed before jobs existed; gh log-failed returned no logs; actionlint 1.7.12 accepted the YAML. Exact server diagnostics were unavailable via the queried API; explicit numeric conversion in the caller and string conversion in the environment allow subsequent run 41192728291 to create jobs |

The stable Release API selected Omarchy v4.0.6, commit
237f1b4071a0bff2296c6d740ba2b9fd695ebfa0, while excluding v4.5.0 RCs. The
vendored network adapter matched and patched a separately downloaded copy of
that fixed upstream source. The reference repository was never modified.

No rootfs Draft, WSL boot, GPU frame, desktop functionality or sustained
stability has passed for this new project at this checkpoint.

Run [41192728291](https://github.com/WSLd-wsx/wsx-rootfs/actions/runs/41192728291),
commit 7663c2dccbb3c2a4078c76d56352a664dbb3ae52, completed compilation and
private staging of all four components, including Hyprland (about 24 minutes
for that compile). Rootfs preparation then failed with "There is no secret key
available to sign with" at pacman-key --lsign-key. The diagnostic artifact retains
all successful component receipts and logs. Initialize the ephemeral builder's
pacman keyring before explicitly trusting the fingerprint-pinned Omarchy key;
keep required package signatures. This is compilation evidence, not a rootfs.
Run 41194901374 was cancelled after this deterministic failure was identified;
its revision had the same missing initialization. Desktop base installation now
precedes compilation, exposing package problems early and using the same
repository configuration for build dependencies and runtime packages.

Run [41195290142](https://github.com/WSLd-wsx/wsx-rootfs/actions/runs/41195290142)
passed explicit keyring initialization and signed repository synchronization,
then failed before compilation because pacstrap required an existing target
directory. Commit 0bbf21c creates that isolated directory. Subsequent runs
41195463319 (r2) and 41195882986 (r3) pass signed desktop base installation.
The r3 contract run [41195878843](https://github.com/WSLd-wsx/wsx-rootfs/actions/runs/41195878843)
passes for commit 4154aea5632e44f574aa9e8b8aa8160c51546357. Its generated-session
regression checks private compositor selection on LINEAR, no opaque enablement,
and rejection of changed compositor bytes without starting a GPU.

Run 41195882986 completes all four component builds and passes the actual rootfs
structure, dependency, account and hygiene checks. Archive admission then refuses
insufficient disk: only 6.6 GiB remains after compiler-intermediate pruning.
No archive or Draft is accepted. The next recipe reclaims unused Android/.NET/GHC
SDKs only on the ephemeral GitHub-hosted runner and removes its own stopped
builder container. It retains the extraction-space guard and all diagnostics.
The captured package configuration also exposes Docker's NoExtract locale/docs
rules and DisableSandboxFilesystem setting; these are removed before desktop
installation, preserving full locale data and normal package sandbox behavior.
