#!/usr/bin/env python3
"""Record installed WSX output/license bindings before offline validation."""
import argparse
from pathlib import Path
from component_materials import verify
from image_licenses import write_image_map

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('work', type=Path)
args = parser.parse_args()
work = args.work.resolve(strict=True)
verify(work)
write_image_map(work/'rootfs', work/'image-materials')
print('Installed module license evidence recorded; active module scope recorded; no public distribution approval')
