#!/usr/bin/env python3
"""Generate review evidence; successful inventory is never release approval."""
import argparse
import fnmatch
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = 'docs/licensing/inventory.json'


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args]).decode()


def inventory():
    rules = json.loads((ROOT / 'docs/licensing/rules.json').read_text())['rules']
    sources = {}
    for name in ('docs/provenance.json', 'components/cachyos-provenance.json'):
        doc = json.loads((ROOT / name).read_text())
        for entry in doc['files']:
            if entry.get('vendored', True):
                path = entry.get('vendored_path', 'vendor/wsx-proto/' + entry['source_path'].removeprefix('prototypes/venus-rutabaga/'))
                sources.setdefault(path, []).append(dict(index=name, source_path=entry['source_path'], reference_commit=entry.get('reference_commit', doc.get('reference_commit')), expected_sha256=entry['sha256']))
    upstream = json.loads((ROOT / 'distros/cachyos-plasma/upstream/source.json').read_text())
    for section in (upstream, upstream['iso_identity']):
        for name, digest in section['files'].items():
            sources.setdefault('distros/cachyos-plasma/upstream/' + name, []).append(dict(index='distros/cachyos-plasma/upstream/source.json', source_path=name, reference_commit=section['commit'], expected_sha256=digest))
    files = sorted(set(filter(None, git('ls-files', '-co', '--exclude-standard', '-z').split('\0'))))
    removed = sorted(set(filter(None, git('ls-files', '-d', '-z').split('\0'))))
    result = []
    for name in files:
        if name == OUTPUT:
            continue  # Avoid a self-referential digest; all other review files are covered.
        path = ROOT / name
        if name in removed and not path.exists() and not path.is_symlink():
            continue  # Record tracked deletions separately, including pending moves.
        if path.is_symlink() or not path.is_file():
            raise ValueError('Unsupported inventory entry: ' + name)
        content = path.read_bytes()
        matches = [r for r in rules if any(fnmatch.fnmatchcase(name, p) for p in r['paths'])]
        if not matches:
            raise ValueError('Uncovered path: ' + name)
        priority = max(r['priority'] for r in matches)
        selected = [r for r in matches if r['priority'] == priority]
        if len(selected) != 1:
            raise ValueError('Ambiguous rules: ' + name)
        rule = selected[0]
        digest = hashlib.sha256(content).hexdigest()
        observations = []
        for number, line in enumerate(content.decode('utf-8', errors='replace').splitlines(), 1):
            if re.search(r'SPDX-|copyright|permission is hereby|licensed under|license|licence', line, re.I):
                kind = 'mention'
                if 'SPDX-' in line or re.search(r'copyright|permission is hereby|licensed under', line, re.I):
                    kind = 'declaration-observation'
                    if name.endswith('.patch'):
                        kind = 'patch-addition' if line.startswith('+') else 'patch-removal' if line.startswith('-') else 'patch-context'
                observations.append(dict(line=number, kind=kind, text=line))
        history = git('log', '--all', '--format=%H', '--', name).splitlines()
        refs = sources.get(name, [])
        for ref in refs:
            ref['hash_matches'] = digest == ref['expected_sha256']
            if not ref['hash_matches']:
                raise ValueError('Source mismatch: ' + name)
        result.append(dict(path=name, sha256=digest, group=rule['group'], rule=rule['id'], basis=rule['basis'], limitation=rule['limitation'], next_step=rule['next_step'], source_index=refs, first_local_commit=history[-1] if history else None, local_change_commits=history, observations=observations))
    active = json.loads((ROOT/'docs/licensing/modules.json').read_text()).get('license_grant', False) if (ROOT/'docs/licensing/modules.json').is_file() else False
    return dict(schema_version=1, head=git('rev-parse', 'HEAD').strip(), license_grant=active, release_ready=False, scope='Git tracked and non-ignored untracked files; excludes this generated inventory, Git internals and ignored build outputs', removed_tracked_paths=removed, files=result)


def content_evidence(document):
    """Compare current bytes/rules; retain commit history as dated snapshot evidence."""
    return {key: ([{k: v for k, v in item.items()
                    if k not in ('first_local_commit', 'local_change_commits')}
                   for item in value] if key == 'files' else value)
            for key, value in document.items()
            if key not in ('head', 'removed_tracked_paths')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--require-release-ready', action='store_true')
    args = parser.parse_args()
    result = inventory()
    encoded = json.dumps(result, indent=2, ensure_ascii=False) + '\n'
    if args.check:
        if content_evidence(json.loads((ROOT / OUTPUT).read_text())) != content_evidence(result):
            raise SystemExit('Inventory stale; regenerate and review')
    else:
        (ROOT / OUTPUT).write_text(encoded)
    print(f"Evidence inventory: {len(result['files'])} files; release_ready=false; active_source_grants={result['license_grant']}")
    if args.require_release_ready:
        raise SystemExit('Public distribution blocked: not authorized; use private-artifact-gate.py for approved private test artifacts')


if __name__ == '__main__':
    main()
