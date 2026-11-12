# SPDX-License-Identifier: GPL-2.0-or-later
"""Apply the WSX Venus session policy to a staged copy of session helpers."""
from pathlib import Path


def configure(directory):
    directory = Path(directory)
    entry = directory / 'enter.py'
    text = entry.read_text()
    if text.count('import os\n') != 1:
        raise ValueError('Unexpected session entry imports')
    text = text.replace('import os\n', 'import os\nimport subprocess\n')
    old = "    os.environ.pop('XAUTHORITY', None)\n    os.execvpe"
    new = """    os.environ.pop('XAUTHORITY', None)
    # Publish the selected policy to D-Bus and systemd before desktop startup.
    if 'VN_PERF' not in os.environ:
        raise RuntimeError('Missing WSX Venus session policy')
    subprocess.run(['/usr/bin/dbus-update-activation-environment', '--systemd', 'VN_PERF'],
                   check=True, timeout=10)
    os.execvpe"""
    if text.count(old) != 1:
        raise ValueError('Unexpected session entry environment')
    entry.write_text(text.replace(old, new))
    launcher = directory / 'wsx-launch-app'
    text = launcher.read_text()
    old = 'MESA_LOADER_DRIVER_OVERRIDE GALLIUM_DRIVER VK_DRIVER_FILES\n'
    if text.count(old) != 1:
        raise ValueError('Unexpected application launcher environment')
    launcher.write_text(text.replace(old, 'MESA_LOADER_DRIVER_OVERRIDE GALLIUM_DRIVER VK_DRIVER_FILES VN_PERF\n'))
