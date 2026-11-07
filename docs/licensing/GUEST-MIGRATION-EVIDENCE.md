# Guest helper migration evidence

Recorded 2026-11-06. These hashes describe observed local bytes, not ownership
or proof that they were the exact bytes at the earlier migration time.

- `guest/protocol-display.py` was introduced in rootfs commit `2b068810e48c72eb620c91b65fb090e7e703df60`; its header identifies `wsld/core/guest/desktop-display.py`. The current wsld checkout is `2858c72e04b543c5c297d1ed626d35df7da1440a`; that source is modified in its working tree, SHA-256 `cc0d60dbf4bebfe7b913601268d7454a080d32655ba6207712c6d299576ed4c0`. Current rootfs copy SHA-256 `d378689db58f69785bd31e5d64e35437ea294ea365e8e6ef07a0b9a42223a4a9`. The exact source-era bytes remain unverified.
- `guest/protocol-retirement.py` was introduced in rootfs commit `2b068810e48c72eb620c91b65fb090e7e703df60`, with an MIT header. Its rootfs SHA-256 is `c02a24f2d93be2a06c1f5b46de6bcb94600ecb3b86ac43b05159100738fd5657`. The precise original wsld path and source-era bytes remain unverified; `wsld/integration/graphics-lifetime/protocol-retirement.py` is a different helper and is not asserted to be the source.
- `guest/input.c` identifies the retained MIT ancestor `vendor/wsx-proto/input/guest.c` in `LICENSE-MAP.md`. Their current SHA-256 values are respectively `bff1b7bd935cbd145d577855e00de9fce47e01107c925e4191cd5e9d5b735d11` and `1f26dd4b3593624bd5653ad55f04602350206cf5ae83e2cb1961d665e346bfeb`. The existing Apache-2.0 protocol header notice remains applicable.

Preserve the existing grants and notices. A later source-era comparison should
record exact original paths, commits and working-tree content without inferring
rights from hashes. No new grant is made by this record.

## Owner rights confirmation

On 2026-11-06 the owner confirmed that `guest/protocol-display.py`,
`guest/protocol-retirement.py` and their wsld sources were independently created
by the owner or adapted from WSX code the owner is entitled to license, without
external-contributor, employer or customer rights. This is an ownership attestation,
not a source-era byte comparison; the original-path and hash gaps above remain.
Existing MIT and PolyForm grants and upstream exceptions remain unchanged.
