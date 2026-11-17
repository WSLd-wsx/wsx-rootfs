#!/usr/bin/env python3
"""Stage the audited Plasma session with instance parameters supplied by core."""
# SPDX-License-Identifier: GPL-2.0-or-later OR Apache-2.0
import argparse
import json
from pathlib import Path
import shutil
import runpy
import subprocess

ROOT = Path(__file__).resolve().parents[1]








def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('rootfs', type=Path)
    p.add_argument('components', type=Path)
    args = p.parse_args()
    root = args.rootfs.resolve(strict=True)
    runtime = root/'usr/lib/wsx/runtime'
    runtime.mkdir(parents=True)
    packages = dict(line.split(' ', 1) for line in (args.components.parent/'rootfs-packages.txt').read_text().splitlines())
    expected_prefixes = {'kwin': '6.8.1-', 'plasma-workspace': '6.8.1-', 'qt6-base': '6.12.0-'}
    for name, prefix in expected_prefixes.items():
        if not packages.get(name, '').startswith(prefix):
            raise ValueError('Private KWin dependency version mismatch: '+name+' '+packages.get(name, '<missing>'))
    lock = {'cpu_architecture_level': 'x86-64-v3', 'packages': {name: packages[name] for name in expected_prefixes}}
    (root/'usr/lib/wsx/plasma-compat.json').write_text(json.dumps(lock, indent=2)+'\n')
    for name in ('mesa', 'venus', 'kwin-opaque'):
        shutil.copytree(args.components/name, runtime/name, symlinks=True)
    helper = root/'usr/lib/plasma-setup-xwayland'
    if not helper.is_file() or not helper.stat().st_mode & 0o111:
        raise ValueError('Missing executable version-locked Plasma Xwayland helper')
    helper_link = root/'opt/wsx/kwin-opaque-6.8.1/lib/libexec/plasma-setup-xwayland'
    helper_link.parent.mkdir(parents=True, exist_ok=True)
    helper_link.symlink_to('/usr/lib/plasma-setup-xwayland')
    shutil.copytree(ROOT/'vendor/wsx-guest-sources/session', runtime/'session')
    runpy.run_path(str(ROOT/'scripts/session_venus_policy.py'))['configure'](runtime/'session')
    subprocess.run(['cc', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
                    '-I'+str(ROOT/'vendor/rvgpu/include'), str(ROOT/'guest/input.c'),
                    '-o', str(runtime/'wsx-input-guest')], check=True)
    init = root/'usr/lib/wsx/initialize-user.sh'
    init.write_text('#!/bin/bash\nset -euo pipefail\nxdg-user-dirs-update\n')
    init.chmod(0o755)

    runpy.run_path(str(ROOT/'scripts/stage-protocol.py'))['stage'](root, 'plasma')


if __name__ == '__main__':
    main()
