#!/usr/bin/env python3
"""Check exact vendored bytes without accessing the reference workspace."""
import hashlib
import json
from pathlib import Path
root = Path(__file__).resolve().parents[1]
for entry in json.loads((root/'docs/provenance.json').read_text())['files']:
    if not entry['vendored']:
        continue
    relative = entry['source_path'].removeprefix('prototypes/venus-rutabaga/')
    actual = hashlib.sha256((root/entry.get('vendored_path', 'vendor/wsx-proto/'+relative)).read_bytes()).hexdigest()
    if actual != entry['sha256']:
        raise SystemExit('Vendored source hash mismatch: ' + relative)
print('Vendored source hashes match the recorded working-tree inputs')
