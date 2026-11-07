#!/usr/bin/env python3
"""Select an already public, verified source-only bundle without changing binaries."""
import argparse
import json
from shared_sources import ROOT, download_index

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--profile',choices=('omarchy','cachyos-plasma'),required=True)
parser.add_argument('--tag',required=True)
parser.add_argument('--sha256',required=True)
args=parser.parse_args()
pin=dict(tag=args.tag,manifest_sha256=args.sha256)
index=json.loads(download_index(pin,args.profile))
if index['profile']!=args.profile:
    raise SystemExit('Shared source profile mismatch')
path=ROOT/'components/source-delivery.json'
config=json.loads(path.read_text())
config['profiles'][args.profile]=pin
path.write_text(json.dumps(config,indent=2)+'\n')
print('Selected public shared source bundle: '+args.tag)
