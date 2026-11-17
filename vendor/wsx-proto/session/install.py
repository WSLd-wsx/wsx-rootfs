#!/usr/bin/env python3
"""Install the common application adapter without changing desktop entries."""
from pathlib import Path
import os
import pwd
import shutil
import sys

account = pwd.getpwnam('omarchy')
home = Path(sys.argv[1]).resolve()
if os.geteuid() != 0 or home != Path(account.pw_dir).resolve():
    raise RuntimeError('Expected the owned Omarchy home and root installer')
target = home / '.local/bin/wsx-launch-app'
target.parent.mkdir(parents=True, exist_ok=True)
source = Path(__file__).resolve().parent / 'wsx-launch-app'
if target.exists() and target.read_bytes() != source.read_bytes():
    backup = target.with_name(target.name + '.before-session-v1')
    if not backup.exists():
        shutil.copy2(target, backup)
        os.chown(backup, account.pw_uid, account.pw_gid)
temporary = target.with_name(target.name + '.session-new')
shutil.copyfile(source, temporary)
os.chmod(temporary, 0o755)
os.chown(temporary, account.pw_uid, account.pw_gid)
os.replace(temporary, target)
