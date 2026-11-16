# Build performance evidence and cache boundary

Run [41195882986](https://github.com/WSLd-wsx/wsx-rootfs/actions/runs/41195882986)
provides these bounded observations on its hosted runner:

| Operation | Observed interval (UTC) | Approximate duration |
| --- | --- | --- |
| Desktop base package transaction | 11:12:46.97 to 11:13:39.37 | 53 seconds |
| Additional compiler dependencies | 11:13:43.44 to 11:13:55.62 | 12 seconds |
| Mesa compilation | 11:14:16.01 to 11:19:20.36 | 5 minutes 4 seconds |
| Venus compilation | 11:19:31.09 to 11:20:30.39 | 59 seconds |
| Aquamarine compilation | 11:20:34.08 to 11:21:33.56 | 59 seconds |
| Hyprland compilation | 11:21:35.59 to 11:41:28.94 | 19 minutes 53 seconds |

The times come from the actual job log, not an estimate from package count.
They do not predict every runner's speed. The desktop transaction downloaded
968.72 MiB and the later compiler transaction downloaded 112.34 MiB; pacstrap
uses the builder's package cache, avoiding duplicate downloads within the run.

The captured rootfs package list contains none of gcc, gdb, cmake, ninja or meson.
The separate builder contains them; gcc-libs is a runtime dependency in the
image. Removing GCC from the compiler environment would prevent the required
private source builds, not merely reduce the final image.

## Next cache optimization

A dependency container pinned by digest may improve environment control, but
caching its installation layers would not eliminate the observed C++ compile
cost. The present workflow runs a pinned container with docker run; BuildKit's
type=gha cache is not automatically active for that operation.

Prefer a verified private-component result cache keyed by architecture, source
archive hashes, patch/builder contents, toolchain and complete installed build
dependency versions. Accept a hit only after receipt/file-hash checks, record its
producing commit/run, and retain the build/runtime dependency equality check.
A rolling package update must invalidate the cache or fail compatibility checks.
Never cache keyrings, credentials, user data or a partially successful component
set. Cache reuse does not establish rootfs or hardware acceptance.

This cache is a proposed follow-up, not an implemented speedup. The current
priority remains the complete Draft build and download verification. Runner SDK
cleanup and removal of the owned stopped container address the observed disk
failure; they do not change package signatures or the extraction-space guard.
