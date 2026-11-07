#!/usr/bin/env python3
"""Validate module review coverage without issuing or activating any license."""
import argparse
import hashlib
import json
from pathlib import Path
from product_licenses import check_boundaries

ROOT = Path(__file__).resolve().parents[1]


def classify(entry, config):
    module = config['path_overrides'].get(entry['path'], config['rule_modules'].get(entry['rule']))
    if module not in config['modules']:
        raise ValueError('Missing module mapping: ' + entry['path'])
    definition = config['modules'][module]
    if definition['polyform_scope'] and entry['group'] != 'conditional-future-license':
        raise ValueError('Existing or unresolved terms cannot default to PolyForm: ' + entry['path'])
    return dict(path=entry['path'], sha256=entry['sha256'], module=module,
                existing_review_group=entry['group'], existing_rule=entry['rule'],
                treatment=definition['treatment'], license_grant=bool(config['license_grant'] and definition.get('new_grant')))


def validate_selection(config):
    selection = config.get('license_selection', {})
    if (selection.get('spdx') != 'PolyForm-Noncommercial-1.0.0'
            or selection.get('unmodified') is not True
            or selection.get('selected_by_owner') is not True
            or selection.get('effective') is not True
            or config.get('activation', {}).get('date') != '2026-11-03'
            or config.get('activation', {}).get('approved_by') != 'WGY (GitHub: wgy-wsx) <wgy@wsxdesk.com>'):
        raise ValueError('Expected owner-approved, active and unmodified PolyForm grant')
    if (selection.get('additional_permissions') != []
            or selection.get('additional_restrictions') != []
            or selection.get('enterprise_evaluation_addendum') is not False):
        raise ValueError('Owner selected standard PolyForm without additions')
    expected_path = 'docs/licensing/licenses/PolyForm-Noncommercial-1.0.0.txt'
    if selection.get('text_path') != expected_path:
        raise ValueError('Unexpected PolyForm reference path')
    path = ROOT / expected_path
    if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != selection['text_sha256']:
        raise ValueError('PolyForm reference bytes changed')
    references = json.loads((ROOT/'docs/licensing/license-text-sources.json').read_text())['files']
    matches = [entry for entry in references if entry['path'] == expected_path]
    if (len(matches) != 1 or matches[0]['sha256'] != selection['text_sha256']
            or matches[0]['url'] != 'https://polyformproject.org/licenses/noncommercial/1.0.0.txt'):
        raise ValueError('PolyForm reference provenance mismatch')


def audit():
    config = json.loads((ROOT/'docs/licensing/modules.json').read_text())
    validate_selection(config)
    check_boundaries(ROOT)
    inventory = json.loads((ROOT/'docs/licensing/inventory.json').read_text())
    if config['license_grant'] is not True or config['release_ready'] is not False:
        raise ValueError('Expected active source grants without public distribution approval')
    names = {entry['path'] for entry in inventory['files']}
    missing = set(config['path_overrides']) - names
    if missing:
        raise ValueError('Module paths missing: ' + ', '.join(sorted(missing)))
    entries = []
    for entry in inventory['files']:
        path = ROOT/entry['path']
        if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError('Refresh source inventory first: ' + entry['path'])
        entries.append(classify(entry, config))
    return dict(schema_version=1, license_grant=True, release_ready=False, files=entries)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='Write generated evidence outside the repository')
    args = parser.parse_args()
    result = audit()
    if args.output:
        if args.output.resolve().is_relative_to(ROOT):
            raise ValueError('Use external audit output to avoid recursive inventory hashes')
        args.output.write_text(json.dumps(result, indent=2)+'\n')
    counts = {}
    for entry in result['files']:
        counts[entry['module']] = counts.get(entry['module'], 0) + 1
    print(json.dumps(dict(module_counts=counts, license_grant=True, release_ready=False)))


if __name__ == '__main__':
    main()
