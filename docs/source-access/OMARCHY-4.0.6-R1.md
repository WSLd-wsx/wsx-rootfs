# Upstream source references for Omarchy 4.0.6-r1

This guide applies only to the rootfs image whose SHA-256 is
`791feaf4b99ea265df2d15f5596713256048d032840d2e8450354a32c1db750a`.
The [package index](omarchy-4.0.6-r1-upstream-packages.json) lists the 599
installed package names and versions, their declared licenses, and the
identified upstream packaging repositories and immutable commits. Each
component retains its own license and notices. The WSX recipe license does
not replace them.

For an Arch package, locate its entry, obtain the `packaging.repository`, and
check out `packaging.commit`. The package's PKGBUILD and adjacent files describe
its source inputs and build instructions. The recorded version tag and commit
are discovery results, not a guarantee that the package's original build used
those exact inputs or that each referenced upstream input remains available.
For the five Omarchy packages, use `packaging.repository`, `packaging.path`,
and one of the listed matching PKGBUILD commits. The `omarchy-keyring` inputs
match two recorded commits; the original build commit has not been determined.

The installed `libfdk-aac 3.0.0-1` library and notice matched the recorded Arch
binary package. Its Arch packaging recipe has no extra patches and points to
the [upstream v3.0.0 source](https://github.com/mstorsjo/fdk-aac/tree/a68a51aa45d86a43c7b228e3d45624af09dcdd8d).
The original [FDK notice](https://github.com/mstorsjo/fdk-aac/blob/v3.0.0/NOTICE)
is included in the image and governs that component. It includes conditions on
providing complete source to binary recipients and does not grant patent
licenses. A source archive and the matching Arch packaging snapshot were also
retained locally for use if the upstream source route becomes unavailable.

WSX-built graphics components have a separate, shared source-only Release,
`graphics-sources-omarchy-fb3b1c6323383422a47d`, linked and bound by the image's
`graphics-sources.json` and `component-source.json`. The component build and
shared-source publication processes own those materials; the rootfs assembly
checks and references them instead of creating a second graphics source bundle.

This guide and index document access routes and the scope of the evidence; they
do not assert that every exact corresponding source and build input is available
or that all distribution obligations have been discharged. The package index is
an additional review document and is not an asset of the existing immutable
rootfs Release. Public access to a repository and its release assets must be
checked when they are made public.
