# Guest bootstrap v2 development slice

The rootfs keeps the distribution's Mesa, Venus and desktop components. The
proposed WSX bootstrap provides a small bounded local control endpoint and stores
independently distributed WSX Guest adapters. The present source implements only
`capabilities`, `adapter.stage`, `adapter.inspect`, `adapter.select`,
`session.pin` and `session.inspect`; activation is explicitly
unsupported. A caller-supplied manifest hash checks integrity only, not publisher
authentication. Selection and lifetime-pin operations check the actual image
profile and expected selection, but are not wired to session launch; pin release, cleanup and rollback are
not yet implemented. Existing Guest desktop scripts have not been migrated.

`scripts/export-guest-adapter.py` derives a candidate from a staged image,
checks its desktop profile, and binds the session entry, generated desktop,
protocol and retirement helpers to files in the same adapter directory. It
records input and output hashes and rejects unexpected source shapes. It does
not install, admit or activate a candidate. The image retains its graphics
components, distribution profile and initialization dependencies; generated
files retain their existing copyright and license notices. The bootstrap still
needs to invoke the catalog-admitted adapter pinned for the session.

Image construction now stages this bootstrap and the adapter store. Offline image
validation checks its capability response, including that activation remains
unsupported. The image's desktop contract is still protocol 1: the existing
desktop entry remains in use until Core and Guest v2 lifecycle integration is
complete. This bootstrap-only staging is not a v2 desktop release and does not
establish desktop, GPU, security or release acceptance.
