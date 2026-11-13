#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Package the Guest protocol; internal layout never becomes a Host API."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]


def stage(root, implementation):
    target = root/'usr/lib/wsx'
    target.mkdir(parents=True, exist_ok=True)
    for source, name in [('protocol.py','guest-protocol.py'),
                         ('protocol-display.py','protocol-display.py'),
                         ('device-view.py','device-view.py'),
                         ('protocol-retirement.py','protocol-retirement.py'),
                         ('bootstrap-v2.py','bootstrap-v2.py'),
                         ('adapter-store.py','adapter-store.py')]:
        shutil.copy2(ROOT/'guest'/source, target/name)
        (target/name).chmod(0o644)
    state = root/'var/lib/wsx'
    state.mkdir(parents=True, exist_ok=True)
    state.chmod(0o700)
    consumer = {'hyprland':'opaque-consumer', 'plasma':'kwin-opaque'}[implementation]
    components = {name:hashlib.sha256((target/'runtime'/name/'manifest.json').read_bytes()).hexdigest()
                  for name in ('mesa','venus',consumer)}
    profile = dict(schema_version=1, implementation=implementation, consumer=consumer,
                   component_manifests=components)
    (target/'guest-profile.json').write_text(json.dumps(profile,sort_keys=True,indent=2)+'\n')
    (target/'guest-profile.json').chmod(0o644)
