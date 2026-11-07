#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Validate manually attested hardware evidence bound to an exact rootfs image."""
import argparse
import hashlib
import json
from pathlib import Path
import re
from contract import parse_install, validate

STAGES = ('wsl_boot', 'account_initialization', 'gpu_first_frame', 'desktop_input', 'normal_stop')
HEX = re.compile(r'[0-9a-f]{64}\Z')

def validate_evidence(evidence, manifest):
    validate(manifest)
    if not isinstance(evidence,dict) or set(evidence) != {'schema_version','tag','archive_sha256','manifest_sha256','observed_at_utc','environment','stages'}:
        raise ValueError('Invalid acceptance evidence fields')
    if type(evidence['schema_version']) is not int or evidence['schema_version'] != 1:
        raise ValueError('Unsupported acceptance evidence schema')
    tag = manifest['distribution_id'] + '-' + manifest['image_version']
    if evidence['tag'] != tag or parse_install(tag)[1] is None or evidence['archive_sha256'] != manifest['sha256']:
        raise ValueError('Evidence does not identify the candidate archive')
    if not isinstance(evidence['manifest_sha256'],str) or not HEX.fullmatch(evidence['manifest_sha256']):
        raise ValueError('Invalid manifest digest')
    if not isinstance(evidence['observed_at_utc'],str) or not re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ',evidence['observed_at_utc']):
        raise ValueError('Invalid UTC observation time')
    env=evidence['environment']
    if not isinstance(env,dict) or set(env) != {'windows_version','wsl_version','gpu_description','graphics_runtime'}:
        raise ValueError('Incomplete acceptance environment')
    if any(not isinstance(v,str) or not v.strip() or len(v)>512 or '\n' in v or '\r' in v for v in env.values()):
        raise ValueError('Invalid acceptance environment value')
    stages=evidence['stages']
    if not isinstance(stages,dict) or set(stages) != set(STAGES):
        raise ValueError('Incomplete acceptance stage set')
    for value in stages.values():
        if not isinstance(value,dict) or set(value)!={'result','source'} or value['result'] not in ('passed','failed','not_run') or value['source'] != 'manual':
            raise ValueError('Invalid manual acceptance stage')
    return evidence

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence',type=Path,required=True);parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--archive',type=Path,required=True);parser.add_argument('--require-passed',action='store_true')
    args=parser.parse_args()
    raw=args.manifest.read_bytes();manifest=json.loads(raw);evidence=validate_evidence(json.loads(args.evidence.read_text()),manifest)
    if hashlib.sha256(raw).hexdigest()!=evidence['manifest_sha256']:
        raise ValueError('Evidence is bound to a different manifest')
    with args.archive.open('rb') as stream: archive_hash=hashlib.file_digest(stream,'sha256').hexdigest()
    if archive_hash != evidence['archive_sha256'] or args.archive.stat().st_size != manifest['compressed_size']:
        raise ValueError('Archive bytes do not match evidence and manifest')
    if args.require_passed and any(v['result']!='passed' for v in evidence['stages'].values()):
        raise ValueError('One or more manual acceptance stages have not passed')
    print(json.dumps({'tag':evidence['tag'],'archive_sha256':archive_hash,'evidence_sha256':hashlib.sha256(args.evidence.read_bytes()).hexdigest(),'trust':'manual attestation; not a publisher signature'},sort_keys=True))
if __name__=='__main__': main()
