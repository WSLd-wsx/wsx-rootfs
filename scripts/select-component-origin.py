#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later OR Apache-2.0
"""Select a successful private component build; admission verifies its bytes."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OPS = 'operations'
RECIPE = 'WSLd-wsx/wsx-rootfs'


def pin_from_log(log, profile, run_id, *, require_profile=False):
    rows = []
    for line in log.splitlines():
        parts = line.split('\t', 2)
        if len(parts) != 3:
            continue
        match = re.match(r'\S+Z (.*)', parts[2])
        if match:
            rows.append((parts[1], re.sub(r'\x1b\[[0-9;]*m', '', match.group(1))))
    profiles = {text.split('PROFILE:',1)[1].strip() for _, text in rows if 'PROFILE:' in text}
    if require_profile and not profiles:
        raise ValueError('Missing component profile in run log')
    if profiles and len(profiles) != 1:
        raise ValueError('Ambiguous component profile in run log')
    if profile not in profiles:
        return None
    blocks = []
    lines = [text for step,text in rows if step == 'Upload and verify paired private GHCR package']
    # GitHub's archived job logs may omit step names; the run identity and
    # package receipt are independently verified before admission below.
    if not lines:
        lines = [text for step,text in rows if step == 'UNKNOWN STEP']
    for i, line in enumerate(lines):
        if line.strip() != '```json':
            continue
        end = next((j for j in range(i+1,len(lines)) if lines[j].strip() == '```'), None)
        if end is None:
            raise ValueError('Incomplete component pin in run log')
        try:
            block = json.loads('\n'.join(lines[i+1:end]))
        except json.JSONDecodeError:
            continue
        if isinstance(block, dict) and block.get('run_id') == run_id and block.get('transport') == 'ghcr':
            blocks.append(block)
    if len(blocks) != 1 or blocks[0].get('run_id') != run_id:
        raise ValueError('Missing or ambiguous verified component pin')
    return blocks[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', required=True, choices=('omarchy','cachyos-plasma'))
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--repository', choices=(OPS, RECIPE), default=OPS)
    args = parser.parse_args()
    token_name = 'WSX_OPS_TOKEN' if args.repository == OPS else 'GH_TOKEN'
    token = os.environ.get(token_name)
    if not token:
        raise ValueError(token_name + ' is required')
    env = dict(os.environ, GH_TOKEN=token)
    runs = json.loads(subprocess.check_output(['gh','run','list','--repo',args.repository,
        '--workflow','components.yml','--branch','main','--status','success',
        '--limit','50','--json','databaseId,status,conclusion,event,headSha'],env=env,text=True))
    spec = importlib.util.spec_from_file_location('reuse_components', ROOT/'scripts/reuse-components.py')
    reuse = importlib.util.module_from_spec(spec); spec.loader.exec_module(reuse)
    for row in runs:
        if row.get('status') != 'completed' or row.get('conclusion') != 'success' or row.get('event') != 'workflow_dispatch':
            continue
        run_id = row['databaseId']
        log = subprocess.check_output(['gh','run','view',str(run_id),'--repo',args.repository,'--log'],env=env,text=True)
        try:
            pin = pin_from_log(log,args.profile,run_id,require_profile=args.repository == RECIPE)
        except (ValueError, json.JSONDecodeError) as error:
            if args.repository == RECIPE:
                raise
            print(f'Skipping component run {run_id}: {error}', flush=True)
            continue
        if pin is None:
            continue
        run = json.loads(subprocess.check_output(['gh','api',f'repos/{args.repository}/actions/runs/{run_id}'],env=env,text=True))
        reuse.validate_origin(pin,args.profile,RECIPE,run,{})
        if args.repository == RECIPE:
            from component_registry import IMAGE
            if (not pin['image'].startswith(IMAGE + '@sha256:')
                    or 'run_repository' in pin or 'workflow_commit' in pin):
                raise ValueError('Unexpected rootfs component origin')
        head = pin['source_commit'] if args.repository == RECIPE else pin.get('workflow_commit')
        if head != row.get('headSha'):
            raise ValueError('Component workflow commit mismatch')
        args.output.write_text(json.dumps(pin,indent=2)+'\n')
        print(json.dumps({'profile':args.profile,'run_id':run_id,'image':pin['image']}))
        return
    raise ValueError('No successful retained component build found for '+args.profile)


if __name__ == '__main__':
    main()
