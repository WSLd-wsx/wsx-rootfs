# Guest bootstrap v2 development slice

The rootfs keeps the distribution's Mesa, Venus and desktop components. The
proposed WSX bootstrap provides a small bounded local control endpoint and stores
independently distributed WSX Guest adapters. The present source implements only
`capabilities`, `adapter.stage`, `adapter.inspect`, `adapter.select`,
`session.pin` and `session.inspect`; fixed dispatch can start a pinned adapter.
A caller-supplied manifest hash checks integrity only, not publisher
authentication. Selection and lifetime-pin operations check the actual image
profile and expected selection. Pin release, cleanup and rollback are not yet
implemented. Desktop behavior is exported from the existing Guest code.

The bootstrap also exposes a fixed `dispatch` process entry for `host-call`,
`prepare`, and `start`, requiring a verified session pin and rechecking the
adapter before execution. It accepts no arbitrary executable or argument list.
This is a routing primitive, not evidence that desktop or GPU startup succeeded.

`scripts/export-guest-adapter.py` derives a candidate from a staged image,
checks its desktop profile, and binds the session entry, generated desktop,
protocol and retirement helpers to files in the same adapter directory. It
records input and output hashes and rejects unexpected source shapes. It does
not install, admit or activate a candidate. The image retains its graphics
components, distribution profile and initialization dependencies; generated
files retain their existing copyright and license notices. The bootstrap still
needs to invoke the catalog-admitted adapter pinned for the session.

Image construction now stages this bootstrap and the adapter store. Offline image
validation checks its capability response; it does not execute a session. The
candidate desktop contract declares bootstrap major 2 and retains adapter wire
protocol major 1 as an independently versioned interface. Existing released
images predate this contract. The candidate is not a desktop release and does
not establish GPU, security or release acceptance.
