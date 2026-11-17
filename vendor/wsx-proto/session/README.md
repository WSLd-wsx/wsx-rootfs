# Common desktop application session

The desktop must be a real PAM/logind user session, not just a root service
spawning a process with setuid. `runuser` uses the installed PAM configuration;
`enter.py` verifies the resulting session and selects `/run/user/<uid>` and the
standard user bus. Omarchy's existing startup environment imports then reach the
same manager used by real UWSM, portals and activation services.

Before compositor startup, only the exact WSLg-injected `wayland-0` links are
moved to explicit backup names in that user's runtime. Owned sockets are never
removed. DISPLAY, WAYLAND_DISPLAY and XAUTHORITY are absent at compositor entry;
applications inherit the display subsequently assigned by Hyprland.

The Guest launcher overlays WSLg's read-only distro X11 socket mount with an
owned writable runtime directory. Explicit WSLg socket names remain available
through links to the original mount. Hyprland's Xwayland selects a free display.
The original WSLg mount and sockets are not modified. No X server is made public.

`wsx-launch-app` contacts the real UWSM daemon, then restores the graphical
caller's display and rendering environment inside its application scope. It
clears stale display variables absent from the caller. It does not rewrite
application desktop entries, replace pkexec, or change authorization policy.
GParted's packaged launcher uses the standard xorg-xhost dependency to grant and
revoke root X11 access around its normal pkexec invocation.

Live deployment-35 repair registers the Omarchy shell agent through a real PAM
session, starts Xwayland on :1, and preserves the compositor. A user menu launch
then produces a visible GParted Xwayland window. A root-origin launch probe is
not equivalent to a menu child of that session and still fails authentication;
keep those observations distinct. The user reports no password prompt. No
passwordless rule was installed and no partition operation was performed.

A separate real PAM entry check verifies the standard runtime, user bus and
absence of inherited displays. Deployment 36 includes the persistent launcher
and these helpers; its full fresh desktop lifecycle remains to be verified.
