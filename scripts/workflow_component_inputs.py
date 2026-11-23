# SPDX-License-Identifier: GPL-2.0-or-later OR Apache-2.0
"""Apply verified workflow-selected component and public-source inputs locally."""
import json
import os
from pathlib import Path
import re
import shared_sources
import component_registry
from operations_provenance import repositories


def apply(root, profile, selection, verify=True):
    if profile not in ('omarchy', 'cachyos-plasma'):
        raise ValueError('Unsupported component profile')
    if not isinstance(selection, dict) or set(selection) != {'component', 'shared_source'}:
        raise ValueError('Invalid workflow component selection')
    pin = selection['component']
    if isinstance(pin, dict) and 'workflow_commit' in pin and 'run_repository' not in pin:
        pin = dict(pin, run_repository=os.environ.get('WSX_OPERATIONS_REPOSITORY', ''))
    required = {'transport', 'image', 'run_id', 'source_commit', 'manifest_sha256'}
    operations_fields = {'run_repository', 'workflow_commit'}
    if not isinstance(pin, dict) or set(pin) not in (required, required | operations_fields):
        raise ValueError('Invalid component origin fields')
    if (pin['transport'] != 'ghcr'
            or type(pin['run_id']) is not int or pin['run_id'] <= 0
            or not re.fullmatch(r'[0-9a-f]{40}', pin['source_commit'])
            or not re.fullmatch(r'[0-9a-f]{64}', pin['manifest_sha256'])):
        raise ValueError('Invalid component origin')
    component_registry.check_reference(pin['image'])
    if 'run_repository' in pin:
        if (pin['run_repository'] not in repositories()
                or not re.fullmatch(r'[0-9a-f]{40}', pin['workflow_commit'])):
            raise ValueError('Invalid operations build origin')
    elif not pin['image'].startswith(component_registry.IMAGE + '@sha256:'):
        raise ValueError('Rootfs builds must use the rootfs component package')
    source = selection['shared_source']
    if not isinstance(source, dict) or set(source) != {'tag', 'manifest_sha256'}:
        raise ValueError('Invalid shared source selection')
    shared_sources.validate_pin(source, profile)
    if verify:
        index = json.loads(shared_sources.download_index(source, profile))
        if index['profile'] != profile:
            raise ValueError('Shared source profile mismatch')
    root = Path(root)
    reuse_path = root/'components/reuse.json'
    delivery_path = root/'components/source-delivery.json'
    reuse = json.loads(reuse_path.read_text())
    delivery = json.loads(delivery_path.read_text())
    if reuse.get('schema_version') != 1 or delivery.get('schema_version') != 1 or delivery.get('mode') != 'shared-v2':
        raise ValueError('Unsupported component configuration')
    reuse['profiles'][profile] = pin
    delivery['component_origins'][profile] = pin
    delivery['profiles'][profile] = source
    reuse_path.write_text(json.dumps(reuse, indent=2)+'\n')
    delivery_path.write_text(json.dumps(delivery, indent=2)+'\n')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', required=True, choices=('omarchy', 'cachyos-plasma'))
    parser.add_argument('--selection', type=Path, required=True)
    args = parser.parse_args()
    apply(Path(__file__).resolve().parents[1], args.profile, json.loads(args.selection.read_text()))
