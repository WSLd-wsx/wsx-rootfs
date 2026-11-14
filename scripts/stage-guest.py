#!/usr/bin/env python3
"""Stage the paired private runtime and the Guest v2 bootstrap."""
# Generator logic: GPL-2.0-or-later; source-expression exceptions below.
# Expression exceptions (also apply to these portions in source form):
# Owner-original strings/replacements inserted into desktop.py are MIT.
# Original session installer adaptations remain GPL-2.0-or-later.
# See docs/licensing/OUTPUT-LICENSES.md and licenses/WSX-MIT.txt.
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import runpy
import subprocess

ROOT=Path(__file__).resolve().parents[1]


def hashes(path):
    result={}
    for p in sorted(path.rglob('*')):
        if p.is_file():
            with p.open('rb') as stream:
                result[str(p.relative_to(path))]=hashlib.file_digest(stream,'sha256').hexdigest()
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('rootfs',type=Path);p.add_argument('components',type=Path);args=p.parse_args()
    root=args.rootfs.resolve();runtime=root/'usr/lib/wsx/runtime';runtime.mkdir(parents=True)
    for name in ('mesa','venus'):
        shutil.copytree(args.components/name,runtime/name,symlinks=True)
    consumer=runtime/'opaque-consumer'
    shutil.copytree(args.components/'opaque-consumer', consumer, symlinks=True)
    for folder in ('session','network'):
        shutil.copytree(ROOT/'vendor/wsx-proto'/folder,runtime/folder)
    runpy.run_path(str(ROOT/'scripts/session_venus_policy.py'))['configure'](runtime/'session')
    # Parameterize the reference session installer; retain its ownership checks.
    installer=runtime/'session/install.py'
    text=installer.read_text().replace("account = pwd.getpwnam('omarchy')", "account = pwd.getpwnam(os.environ['WSX_USER'])")
    installer.write_text(text)
    subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror',
                    '-I'+str(ROOT/'vendor/rvgpu/include'),str(ROOT/'guest/input.c'),
                    '-o',str(runtime/'wsx-input-guest')],check=True)
    for source,target in [('guest/initialize-user.sh','usr/lib/wsx/initialize-user.sh')]:
        shutil.copy2(ROOT/source,root/target);(root/target).chmod(0o755)
    (root/'usr/lib/wsx/runtime-files.json').write_text(json.dumps(hashes(runtime),indent=2)+'\n')

    runpy.run_path(str(ROOT/'scripts/stage-protocol.py'))['stage'](root, 'hyprland', bootstrap_only=True)


if __name__=='__main__': main()
