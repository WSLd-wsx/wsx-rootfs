# CachyOS Plasma candidate evidence

## r2 Draft after runtime handoff

Run [41269754558](https://github.com/WSLd-wsx/wsx-rootfs/actions/runs/41269754558)
built commit `2091dc5bac6340325612f5d3c9c002327329e7ef` and completed
[Draft 2026.11.1-r2](https://github.com/WSLd-wsx/wsx-rootfs/releases/tag/untagged-332d9d88866fdce8dbf9).
The 2,015,878,334-byte archive SHA-256 is
`154e8c959cfbaadaaf58c46b44ac6458c3992b3b14a336667f58079efc2c2645`.
Build, offline checks and remote asset byte verification passed. WSL boot, GPU
first frame, desktop and stability are all `not_run` for this image. The r1
trial after manual adjustments does not establish r2 hardware acceptance.

Run 41269642059 was intentionally cancelled before publication when the
session ownership record was added; its uncompleted candidate was not released.
The r2 adapter retains failed-session ownership evidence and refuses automatic
socket removal or failed-unit reset. Its normal logout and retry still require
real-machine acceptance, and device ACL and input reconnect remain core tasks.

## Published Draft candidate

Run [41265853391](https://github.com/WSLd-wsx/wsx-rootfs/actions/runs/41265853391)
built commit `aa195a7f46e7f257fdf08bb09d5135646e62583e` and completed
[Draft 2026.11.1-r1](https://github.com/WSLd-wsx/wsx-rootfs/releases/tag/untagged-8f0bd477b40972ce2cd9)
on its publication retry. The date identifies this WSX snapshot, not an official
CachyOS release. Build and offline checks passed; WSL boot, GPU first frame,
desktop and stability acceptance remain untested. Publication verified the remote
asset bytes before uploading `completion.json`.

The 2,015,809,410-byte archive has SHA-256
`481b794cee452487e1da31eb796e5f5f3da6ad178b21944ccbd54c017e032488`.
Its logical unpacked size is 5,837,917,729 bytes; compression used zstd level 15,
two threads, 458.26 seconds and a peak RSS of 280,708 KiB. Archive extraction
verification covered ownership, modes, links, xattrs, ACLs, capabilities and
file hashes. The archive approaches GitHub's 2 GiB per-asset limit.

The first publication attempt created the Draft but failed when it was not yet
visible in the subsequent release listing. Retrying only the publication job
completed the same verified candidate. A bounded visibility retry was added
afterward and covered by contract tests; creation of another Draft has not been
used to verify that change remotely. GitHub rejected a dispatch using the exact
old commit SHA as a ref, so remote deduplication of this precise identity was not
verified by a second workflow run.

The first signed package bootstrap (run 41263692927) completed successfully;
its workflow deliberately failed afterward because the Guest recipe was not yet
ready. Run 41264900094 installed the fixed Arch snapshot, staged the private
Plasma runtime and passed offline validation. It was cancelled during archiving
because official OS identity and complete local-keyring cleanup were added later.
It is not a released image and is not real WSL/GPU acceptance.

Its package record included `kwin 6.8.1-2`, `plasma-workspace 6.8.1-1`,
`qt6-base 6.12.0-3`, `shelly 3.1.10-1` and `cachyos-kde-settings 4.9-8`.
The historical KWin binary's ELF notes require x86-64-v3. The reference
`cachyos-opaque-lifecycle-02` demonstrated bounded Iris Xe desktop presentation,
logout and same-instance restart, with a remaining device-teardown warning.
This does not establish acceptance of the new image or another GPU.

The build combines the fixed Arch 2026-10-28 package snapshot with the rolling
CachyOS repository. Pacman validates package signatures and declared package
dependencies, but different repository epochs can still introduce ABI or runtime
incompatibilities. This is not a synchronized distribution snapshot or a byte
reproducibility claim. The private ELF dependency checks do not test every desktop
application. Preserve this limitation and perform actual Shelly, desktop and
upgrade tests before any public release. A future build should lock a synchronized
CachyOS repository state or rebuild the private graphics stack against the
current distribution release.

A read-only local binary inspection, without installation or execution, observed
that the official Shelly 3.1.10 CLI requires `libalpm.so.16` and that the selected
Arch pacman 7.1.0.r9.g54d9411-3 package contains that SONAME. The downloaded
package SHA-256 values were respectively
`cf8afe89098067732fba6b0fe64a7f33f48acf7021e858ea95b7eca46531fda1` and
`bad000f7b482c7f5e6c8e6951d918ce8a9207c0f9c0786ab2b49fe75e935de28`.
This inspection used HTTPS and did not independently verify package signatures;
CI's normal signed pacman transaction provides installation integrity. Matching
one SONAME does not establish Shelly GUI or Polkit functionality.

## Preserved candidate attempts

The following runs were cancelled before publication when a concrete admission
requirement was discovered. Their logs remain available in Actions:

- 41264087951: rolling KWin/Plasma had advanced beyond the paired private KWin;
  the private executable also required an explicit x86-64-v3 CPU contract.
- 41264418676: KWin patch and adapter provenance was being completed.
- 41264526288: first-user creation of the local package-signing key was added.
- 41264692257: exact installed Plasma/Qt package revisions were added to the
  runtime compatibility lock.
- 41264900094: signed bootstrap and offline Guest checks passed; the build was
  stopped before publication so the final recipe could remove the entire build
  keyring and install the pinned official CachyOS identity files.

These cancellations do not establish failures of the checks that had already
passed, nor do they establish success of checks that had not run.

## Post-publication real-machine trial

The 2026-11-01 Iris Xe trial reached visible Plasma after local corrections;
the unchanged Draft did not pass first desktop startup. See the
[runtime handoff](cachyos-r1-runtime-handoff.md) for rootfs/core ownership,
evidence hashes, unresolved recovery and the new-revision acceptance checklist.
The earlier untested statements above describe publication-time evidence.

## r2 clean-import acceptance (2026-11-01)

Draft `wsx-cachyos-plasma-2026.11.1-r2`, build
`2091dc5bac6340325612f5d3c9c002327329e7ef`, was downloaded in the active terminal,
verified and imported as a new distro. Archive SHA-256:
`154e8c959cfbaadaaf58c46b44ac6458c3992b3b14a336667f58079efc2c2645`.
No image code or helper-path patch was needed. Initialization enabled user linger;
the packaged Xwayland helper resolved correctly. Dynamic instance-checked DRM
ACLs and receipt-checked Windows input reconnection were supplied by core test
adapters, not by image-specific user/GID changes.

On Iris Xe driver 31.0.101.5081 and kernel 6.18.54.1, opaque-v1 presented 1,129
frames in the first session. A real Xwayland xmessage window was captured and
reported exit 0. The session ran 126.102 seconds, exited 0 through normal logout,
retired KWin before input/seat, removed its owner record and socket, and completed
native context 2 destruction. No failed-unit reset or manual socket cleanup was
required. The same host/PCI instance restarted successfully after checked input
reconnection and presented another 1,795 frames by the 12:30:42 +08:00 cutoff.
There were no queue command errors or nonzero presentation results in that log.
Systemd reported no failed units. Staging stayed disabled; WSL was not restarted.

This validates RF-1/RF-2 startup integration and the normal RF-3 session lifecycle
for this bounded trial, not all abnormal-recovery branches. Initial output was
784x441. Input transport recorded 447 packets with zero drops before logout;
separate human keyboard/mouse confirmation and sudo/Polkit password authentication
remain pending. Sustained stress, RTX and full r2 native device teardown are not
accepted. A virtio_dev_remove warning from prior r1 device removal was already
visible before r2 graphics startup; do not claim warning-free device teardown.
Core helpers remain validation adapters, not completed shipped client integration.
The r2 desktop remains running.

Evidence is local to wsx-proto under
`artifacts/venus-rutabaga/rootfs-cachyos-r2-start-01/`: result.json, native.log,
session-journal.log, start/stop/restart logs, core adapter scripts, xwayland.png
and restarted-desktop.png. Preserve publication-time validation metadata and
historical r1 failures; this is a separate post-publication acceptance record.

Evidence SHA-256:

- `result.json`: `0d1f8c7c66cb68793201c65b68e33a2323bd7e41fc220ffea9feeea79def4674`
- `session-journal.log`: `97d1aceeac1e0371f605b94f016e4a212ceff601c69295a1832b3d7ff95e8ab3`
- `xwayland.png`: `cb16c600a3a06067d27e15948a6f761123de485b64f9bcfacfc30c19578deb02`
- `restarted-desktop.png`: `bfc1ade7d63148c793ae0bed9ddeef9a82b760412c2a85810373f80c6145dc04`
