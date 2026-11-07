"""Pair source evidence with rootfs payloads without claiming legal completeness."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
from component_materials import sha, verify

from payload_contract import SOURCE_ASSETS as NAMES
from payload_contract import SHARED_SOURCE_ASSETS
import shared_sources

ROOT = Path(__file__).resolve().parents[1]

# This retired installer reference is not used by either rootfs recipe.
# Match both path and pinned bytes before excluding anything from delivery.
RETIRED_INPUTS = {
    'distros/cachyos-plasma/upstream/netinstall.yaml': '9f29e5ea796a30b43c1e4a1367960694fb2a620fd88c2911795b4e9460143486',
}


def project_sources(payload, profile):
    """Omit unrelated unresolved inputs from a copy; keep original GHCR evidence."""
    import hashlib
    report = json.loads((payload/NAMES[1]).read_text())
    excluded = {'recipe/' + path: digest for path, digest in RETIRED_INPUTS.items()}
    removed = []
    archive_path = payload/NAMES[0]
    original_sources = dict(report['sources'])
    with tempfile.TemporaryDirectory(dir=payload, prefix='source-projection-') as temporary:
        projected = Path(temporary)/'sources.tar'
        with tarfile.open(archive_path, 'r:') as source, tarfile.open(projected, 'w') as target:
            seen = set()
            for member in source:
                if member.name in seen:
                    raise ValueError('Duplicate source member: ' + member.name)
                seen.add(member.name)
                if member.name in excluded:
                    if not member.isfile():
                        raise ValueError('Excluded source must be a regular file')
                    with source.extractfile(member) as stream:
                        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
                    if digest != excluded[member.name]:
                        raise ValueError('Excluded source differs from reviewed input: ' + member.name)
                    removed.append(dict(path=member.name, sha256=digest, size=member.size))
                    continue
                if member.isfile():
                    with source.extractfile(member) as stream:
                        target.addfile(member, stream)
                else:
                    target.addfile(member)
        recorded = [entry for entry in report['source_entries'] if entry['path'] in excluded]
        if sorted(recorded, key=lambda item: item['path']) != sorted(removed, key=lambda item: item['path']):
            raise ValueError('Excluded material does not match its recorded entry')
        projected.replace(archive_path)
    report['source_entries'] = [entry for entry in report['source_entries'] if entry['path'] not in excluded]
    report['source_projection'] = dict(schema_version=1, profile=profile, excluded=removed,
        original_sources=original_sources,
        reason='Retired installer reference omitted; no compiled component source, patch or license removed')
    report['sources'].update(sha256=sha(archive_path), size=archive_path.stat().st_size)
    (payload/NAMES[1]).write_text(json.dumps(report, indent=2)+'\n')


def retain_image_recipe(work, payload):
    """Append current assembly inputs without changing the admitted component bundle."""
    report = json.loads((payload/NAMES[1]).read_text())
    originals = dict(report.get('source_projection', {}).get('original_sources', report['sources']))
    profile = json.loads((work/'component-source.json').read_text()).get('profile')
    names = subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z',
        'LICENSE','LICENSE-MAP.md','scripts','distros','guest','components','vendor','schema',
        'docs/private-prereleases.md','docs/licensing/THIRD-PARTY-NOTICES.md',
        'docs/provenance.json','docs/licensing/OUTPUT-LICENSES.md','docs/licensing/PRIVATE-ARTIFACTS.md','docs/licensing/modules.json','docs/licensing/rules.json',
        'docs/licensing/license-text-sources.json','docs/licensing/licenses'],cwd=ROOT).decode().split('\0')
    entries = []
    omitted = []
    with tarfile.open(payload/NAMES[0], 'a') as archive:
        existing = set(archive.getnames())
        def add(path, name):
            if name in existing or path.is_symlink() or not path.is_file():
                raise ValueError('Unsafe or duplicate rootfs recipe material: '+name)
            existing.add(name)
            archive.add(path,arcname=name,recursive=False)
            entries.append(dict(path=name,sha256=sha(path),size=path.stat().st_size))
        for name in sorted(set(filter(None,names))):
            path = ROOT/name
            if not path.resolve().is_relative_to(ROOT.resolve()):
                raise ValueError('Rootfs recipe escapes repository')
            if name in RETIRED_INPUTS:
                if not path.exists():
                    continue
                if sha(path) != RETIRED_INPUTS[name]:
                    raise ValueError('Excluded rootfs input changed: ' + name)
                omitted.append(dict(path=name, sha256=sha(path), size=path.stat().st_size))
                continue
            add(path,'rootfs-recipe/'+name)
        add(work/'component-reuse.json','rootfs-recipe/component-reuse.json')
        add(work/'component-materials/materials.json','rootfs-recipe/original-component-materials.json')
    report['source_entries'].extend(entries)
    report['reused_component_sources'] = originals
    report['rootfs_recipe_entries'] = entries
    report['omitted_rootfs_recipe_inputs'] = omitted
    report['sources'].update(sha256=sha(payload/NAMES[0]),size=(payload/NAMES[0]).stat().st_size)
    (payload/NAMES[1]).write_text(json.dumps(report,indent=2)+'\n')


def attach(work, payload):
    if verify(work)['schema_version'] != 1:
        raise ValueError('Compact component materials require schema-2 rootfs delivery')
    originals = (work/'component-materials/sources.tar',
                 work/'component-materials/materials.json', work/'component-source.json')
    files = []
    for name, source in zip(NAMES, originals):
        if source.stat().st_size >= 2**31:
            raise ValueError('Source asset exceeds upload limit; reviewed splitting/compression required')
        target = payload/name
        if target.exists():
            raise ValueError('Source asset already exists: ' + name)
        shutil.copy2(source, target)
    receipt = json.loads((work/'component-source.json').read_text())
    if receipt.get('profile') in ('omarchy', 'cachyos-plasma'):
        project_sources(payload, receipt['profile'])
    if (work/'component-reuse.json').is_file():
        retain_image_recipe(work, payload)
    for name in NAMES:
        target = payload/name
        if target.stat().st_size >= 2**31:
            raise ValueError('Paired source asset exceeds upload limit')
        files.append(dict(name=name, sha256=sha(target), size=target.stat().st_size))
    return dict(schema_version=1, files=files, corresponding_source_complete=False,
                license_review='pending', scope='Paired component source evidence; full image closure pending')


def required_assets(directory, sources):
    delivery = sources.get('component_source_delivery')
    receipt = sources.get('component_source', sources.get('component_package', {}))
    if delivery is None:
        if receipt.get('origin') == 'source-build':
            raise ValueError('Source-built payload requires paired source assets')
        return []  # Historical protocol fixtures are not new publication approval.
    if delivery.get('schema_version') == 2:
        return required_shared_assets(directory, sources)
    if delivery.get('schema_version') != 1:
        raise ValueError('Unknown source delivery schema')
    files = delivery.get('files', [])
    if [entry['name'] for entry in files] != list(NAMES):
        raise ValueError('Source delivery asset set mismatch')
    for entry in files:
        path = directory/entry['name']
        if path.is_symlink() or not path.is_file():
            raise ValueError('Missing regular source asset: ' + entry['name'])
        if sha(path) != entry['sha256'] or path.stat().st_size != entry['size']:
            raise ValueError('Source asset changed: ' + entry['name'])
    material = json.loads((directory/NAMES[1]).read_text())
    actual_receipt = json.loads((directory/NAMES[2]).read_text())
    if actual_receipt != receipt or material['source_receipt_sha256'] != sha(directory/NAMES[2]):
        raise ValueError('Source delivery receipt mismatch')
    if material['sources']['sha256'] != sha(directory/NAMES[0]) or material['sources']['size'] != (directory/NAMES[0]).stat().st_size:
        raise ValueError('Source delivery archive mismatch')
    if material.get('collection_complete') is not True:
        raise ValueError('Incomplete source collection')
    projection = material.get('source_projection')
    if projection is not None:
        if projection.get('schema_version') != 1 or projection.get('profile') not in ('omarchy', 'cachyos-plasma') or actual_receipt.get('profile') != projection.get('profile'):
            raise ValueError('Unexpected source projection')
        blocked = {prefix + name for prefix in ('recipe/', 'rootfs-recipe/') for name in RETIRED_INPUTS}
        with tarfile.open(directory/NAMES[0], 'r:') as archive:
            if any(member.name in blocked for member in archive):
                raise ValueError('Retired input reintroduced into source delivery')
    return list(NAMES)


def attach_current(work, payload):
    """New images carry their own recipe and a verified public shared-source index."""
    verify(work)
    receipt = json.loads((work/'component-source.json').read_text())
    pin = shared_sources.pin_for(ROOT, receipt['profile'])
    index_bytes = shared_sources.download_index(pin, receipt['profile'])
    index = shared_sources.validate_index(json.loads(index_bytes), receipt)
    if index['source_receipt_sha256'] != sha(work/'component-source.json'):
        raise ValueError('Shared source receipt bytes differ from admitted component')
    for name in SHARED_SOURCE_ASSETS:
        if (payload/name).exists():
            raise ValueError('Source delivery destination already exists')
    (payload/'graphics-sources.json').write_bytes(index_bytes)
    shutil.copy2(work/'component-source.json', payload/'component-source.json')
    names = subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z',
        'LICENSE','LICENSE-MAP.md','scripts','distros','guest','components','vendor','schema',
        'docs/private-prereleases.md','docs/licensing/THIRD-PARTY-NOTICES.md','docs/provenance.json',
        'docs/licensing/OUTPUT-LICENSES.md','docs/licensing/PRIVATE-ARTIFACTS.md','docs/licensing/modules.json',
        'docs/licensing/rules.json','docs/licensing/license-text-sources.json','docs/licensing/licenses'],cwd=ROOT).decode().split('\0')
    entries = []
    with shared_sources.deterministic_tar(payload/'image-recipe.tar.gz') as archive:
        for name in sorted(set(filter(None,names))):
            path = ROOT/name
            if name in RETIRED_INPUTS:
                if path.exists():
                    raise ValueError('Retired input reintroduced into current recipe')
                continue
            if path.is_symlink() or not path.resolve().is_relative_to(ROOT.resolve()) or not path.is_file():
                raise ValueError('Unsafe image recipe input: '+name)
            entries.append(shared_sources.add_bytes(archive,'rootfs-recipe/'+name,path.read_bytes(),path.stat().st_mode & 0o777))
        for name in ('component-reuse.json','image-materials/image-source.json',
                     'image-materials/component-materials/notices/MODULE-LICENSES.json',
                     'image-materials/component-materials/notices/MODULE-NOTICES.txt'):
            if (work/name).is_file():
                entries.append(shared_sources.add_bytes(archive,'rootfs-recipe/'+name,(work/name).read_bytes()))
    delivery = dict(schema_version=2, shared_source=pin, recipe_entries=entries,
        files=[dict(name=n,sha256=sha(payload/n),size=(payload/n).stat().st_size) for n in SHARED_SOURCE_ASSETS],
        corresponding_source_complete=False,
        scope=('Image recipe plus an authenticated private digest-pinned shared graphics source bundle; system package source obligations remain separate'
               if os.environ.get('WSX_PRIVATE_SOURCE') == '1' else
               'Image recipe plus a public digest-pinned shared graphics source bundle; system package source obligations remain separate'))
    required_shared_assets(payload, dict(component_source=receipt,component_source_delivery=delivery))
    return delivery


def required_shared_assets(directory, sources):
    delivery = sources['component_source_delivery']
    if [r['name'] for r in delivery.get('files',[])] != list(SHARED_SOURCE_ASSETS):
        raise ValueError('Shared delivery asset set mismatch')
    for row in delivery['files']:
        path = directory/row['name']
        if path.is_symlink() or not path.is_file() or sha(path) != row['sha256'] or path.stat().st_size != row['size']:
            raise ValueError('Shared delivery asset missing or changed: '+row['name'])
    receipt = json.loads((directory/'component-source.json').read_text())
    if receipt != sources.get('component_source', sources.get('component_package',{})):
        raise ValueError('Shared component receipt mismatch')
    index = shared_sources.validate_index(json.loads((directory/'graphics-sources.json').read_text()), receipt)
    pin = delivery['shared_source']
    shared_sources.validate_pin(pin, receipt['profile'])
    if (index['tag'] != pin['tag'] or sha(directory/'graphics-sources.json') != pin['manifest_sha256']
            or index['source_receipt_sha256'] != sha(directory/'component-source.json')):
        raise ValueError('Shared source reference/receipt mismatch')
    records = {r['path']:r for r in delivery.get('recipe_entries',[])}
    if not records or len(records) != len(delivery['recipe_entries']):
        raise ValueError('Missing or duplicate image recipe inventory')
    seen = set()
    with tarfile.open(directory/'image-recipe.tar.gz','r:gz') as archive:
        for member in archive:
            shared_sources.relative(member.name)
            if (not member.isfile() or member.name in seen or member.name not in records
                    or not member.name.startswith('rootfs-recipe/')
                    or member.name.removeprefix('rootfs-recipe/') in RETIRED_INPUTS):
                raise ValueError('Unsafe image recipe member')
            seen.add(member.name)
            row = records[member.name]
            import hashlib
            with archive.extractfile(member) as stream:
                digest = hashlib.file_digest(stream,'sha256').hexdigest()
            if digest != row['sha256'] or member.size != row['size'] or member.mode != row['mode']:
                raise ValueError('Image recipe inventory mismatch')
    if seen != set(records):
        raise ValueError('Image recipe inputs missing')
    return list(SHARED_SOURCE_ASSETS)


def check_public_source_delivery(directory, sources):
    delivery = sources.get('component_source_delivery',{})
    if delivery.get('schema_version') == 2:
        required_shared_assets(directory, sources)
        shared_sources.verify_public(delivery['shared_source'],json.loads((directory/'graphics-sources.json').read_text()))


def check_private_source_delivery(directory, sources):
    delivery = sources.get('component_source_delivery', {})
    if delivery.get('schema_version') != 2:
        raise ValueError('Private source delivery requires schema 2')
    required_shared_assets(directory, sources)
    shared_sources.verify_private(delivery['shared_source'], json.loads((directory/'graphics-sources.json').read_text()))
