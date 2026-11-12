#!/usr/bin/env python3
"""Enter the real PAM session without inheriting WSLg's default display."""
import os
import subprocess
from pathlib import Path
import sys


def main():
    uid = os.getuid()
    runtime = Path(f'/run/user/{uid}')
    if not uid or not os.environ.get('XDG_SESSION_ID') or runtime.stat().st_uid != uid:
        raise RuntimeError('A real non-root PAM user session is required')
    # These are WSLg-injected links, not owned sockets. Retain them under
    # explicit backup names so libwayland's default cannot select WSLg.
    for name in ('wayland-0', 'wayland-0.lock'):
        path = runtime / name
        expected = Path('/mnt/wslg/runtime-dir') / name
        if path.is_symlink() and path.resolve() == expected.resolve():
            backup = runtime / ('.wsx-wslg-' + name)
            if backup.is_symlink() and backup.readlink() == path.readlink():
                path.unlink()
            elif not backup.exists() and not backup.is_symlink():
                path.rename(backup)
            else:
                raise RuntimeError('Conflicting WSLg display-link backup')
    os.environ['XDG_RUNTIME_DIR'] = str(runtime)
    os.environ['DBUS_SESSION_BUS_ADDRESS'] = f'unix:path={runtime}/bus'
    os.environ.pop('DISPLAY', None)
    os.environ.pop('WAYLAND_DISPLAY', None)
    os.environ.pop('XAUTHORITY', None)
    # Publish the negotiated Venus policy before desktop services can activate.
    # An empty value disables the WSX staging option for zero-copy.
    if 'VN_PERF' not in os.environ:
        raise RuntimeError('Missing WSX Venus session policy')
    subprocess.run(['/usr/bin/dbus-update-activation-environment', '--systemd', 'VN_PERF'],
                   check=True, timeout=10)
    os.execvpe(sys.argv[1], sys.argv[1:], os.environ)


if __name__ == '__main__':
    main()
