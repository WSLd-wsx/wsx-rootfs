# Protocol-aware Windows runtime pairing

This is a metadata snapshot of the locally built, byte-verified protocol-aware
Native bundle, not a Windows binary distribution. Rootfs compilation needs only
the declared protocol and receipt; it must not depend on a sibling checkout.
Core verifies actual runtime bytes independently before startup.

Receipt SHA-256: `617965791e6928e535a47ccff46b63983455e5f9dbcc581446776d3654841a10`.
Local build evidence: wsld `artifacts/graphics-protocol-pair-20261105-01`.
Native SHA-256: `fef6d773ae3494c0dc219268dfc840d6adee03f257824139e2aa2c34fe4075da`.
The receipt's complete file size/hash closure was checked before this snapshot
was added. The build reuses the verified renderer and device lifecycle, adding
the public Guest session-stop adapter. New-protocol rootfs hardware acceptance
is pending; no image's validation status is changed by this pin.

The runtime is not downloaded or installed by rootfs CI. Product runtime delivery
remains Core's responsibility. Kernel release and symbol checks remain necessary
on the actual machine. Changing this pin requires a reviewed, actually built
protocol-compatible runtime and a new image revision; editing hashes does not
establish compatibility or authorize publication.
