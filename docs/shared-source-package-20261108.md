# Shared graphics source package migration

The private operations workflow at commit `f9a9af1` recovered and published
source-only OCI artifacts from rootfs commit `fffa1ade08b881bdd758f72c20486e20f713da67`.
Both runs verified the original component origin, source index, complete bundle
and authenticated registry read-back. They did not rebuild graphics binaries.

| Profile | Operations run | OCI manifest digest | Source index SHA-256 |
| --- | --- | --- | --- |
| Omarchy | 42442511128 | `sha256:01c86c76a7d1406b169e9c483e928ba6df56e4bb5d5987e01d8f654500f6929e` | `5ee720a75fb78fa580879bdae6f48144b1920b0f65884479b772d4f21a1def72` |
| CachyOS Plasma | 42442512134 | `sha256:1c1fdf7210557b5b3d479de04856cf314737337cad970ec609963eede44fd159` | `e8d071e730ad5bd3fded22c51c122f1158592539fb59dd078b0477e99f5332b9` |

The package `ghcr.io/wsld-wsx/wsx-rootfs/graphics-sources` was private at
publication. Anonymous access returned HTTP 401; public access and package
pin activation remain pending. Existing release-based pins remain active. Run
the selection procedure in `components/SOURCE-DELIVERY.md` only after changing
the package visibility and checking anonymous retrieval. Do not infer hardware
acceptance from source package verification.
