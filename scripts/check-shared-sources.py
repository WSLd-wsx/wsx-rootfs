#!/usr/bin/env python3
"""Fail before image assembly when shared source delivery is unavailable."""
import argparse
import json
import os
from shared_sources import ROOT, pin_for, download_index

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--profile',choices=('omarchy','cachyos-plasma'),required=True)
args=parser.parse_args()
pin=pin_for(ROOT,args.profile)
index=json.loads(download_index(pin,args.profile))
if index['profile']!=args.profile:
    raise SystemExit('Shared source profile mismatch')
print(('Private' if os.environ.get('WSX_PRIVATE_SOURCE') == '1' else 'Public')
      + ' shared graphics sources verified: '+index['tag'])
