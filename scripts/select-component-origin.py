#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Select a successful private component build; admission verifies its bytes."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OPS = 'WSLd-wsx/wsx-rootfs-ops'
RECIPE = 'WSLd-wsx/wsx-rootfs'


def pin_from_log(log, profile, run_id):
    rows = []
    for line in log.splitlines():
        parts = line.split('\t', 2)
        if len(parts) != 3:
            continue
        match = re.match(r'\S+Z (.*)', parts[2])
        if match:
            rows.append((parts[1], re.sub(r'\x1b\[[0-9;]*m', '', match.group(1))))
    profiles = {text.split('PROFILE:',1)[1].strip() for _, text in rows if 'PROFILE:' in text}
    if profile not in profiles:
        return None
    if profiles != {profile}:
        raise ValueError('Ambiguous component profile in run log')
    blocks = []
    lines = [text for step,text in rows if step == 'Upload and verify paired private GHCR package']
    for i, line in enumerate(lines):
        if line.strip() != '```json':
            continue
        end = next((j for j in range(i+1,len(lines)) if lines[j].strip() == '```'), None)
        if end is None:
            raise ValueError('Incomplete component pin in run log')
        blocks.append(json.loads('\n'.join(lines[i+1:end])))
    if len(blocks) != 1 or blocks[0].get('run_id') != run_id:
        raise ValueError('Missing or ambiguous verified component pin')
    return blocks[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', required=True, choices=('omarchy','cachyos-plasma'))
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    token = os.environ.get('WSX_OPS_TOKEN')
    if not token:
        raise ValueError('WSX_OPS_TOKEN is required')
    env = dict(os.environ, GH_TOKEN=token)
    runs = json.loads(subprocess.check_output(['gh','run','list','--repo',OPS,'--workflow','components.yml',
        '--limit','50','--json','databaseId,status,conclusion,event,headSha'],env=env,text=True))
    spec = importlib.util.spec_from_file_location('reuse_components', ROOT/'scripts/reuse-components.py')
    reuse = importlib.util.module_from_spec(spec); spec.loader.exec_module(reuse)
    for row in runs:
        if row.get('status') != 'completed' or row.get('conclusion') != 'success' or row.get('event') != 'workflow_dispatch':
            continue
        run_id = row['databaseId']
        log = subprocess.check_output(['gh','run','view',str(run_id),'--repo',OPS,'--log'],env=env,text=True)
        pin = pin_from_log(log,args.profile,run_id)
        if pin is None:
            continue
        run = json.loads(subprocess.check_output(['gh','api',f'repos/{OPS}/actions/runs/{run_id}'],env=env,text=True))
        reuse.validate_origin(pin,args.profile,RECIPE,run,{})
        if pin.get('workflow_commit') != row.get('headSha'):
            raise ValueError('Component workflow commit mismatch')
        args.output.write_text(json.dumps(pin,indent=2)+'\n')
        print(json.dumps({'profile':args.profile,'run_id':run_id,'image':pin['image']}))
        return
    raise ValueError('No successful retained component build found for '+args.profile)


if __name__ == '__main__':
    main()
