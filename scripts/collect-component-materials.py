#!/usr/bin/env python3
"""Collect reviewable source/build materials and notices for a fresh source build."""
import argparse
from pathlib import Path
from component_materials import prepare
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('work',type=Path)
a=p.parse_args()
prepare(a.work)
print('Source and notice materials collected; distribution approval remains separate.')
