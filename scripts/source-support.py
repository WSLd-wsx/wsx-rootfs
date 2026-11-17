#!/usr/bin/env python3
"""Check source recipe availability without downloading or publishing."""
import argparse
from source_support import require_source_recipe
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('distribution')
a = p.parse_args()
try:
    require_source_recipe(a.distribution)
except ValueError as error:
    raise SystemExit(str(error))
print('Source compilation recipe available; runtime and publication acceptance are separate.')
