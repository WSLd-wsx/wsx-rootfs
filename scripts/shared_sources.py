"""Project immutable component evidence into reusable, separately licensed sources."""
from contextlib import contextmanager
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
from urllib.request import Request, urlopen

from component_materials import relative, sha, verify

REPOSITORY = 'WSLd-wsx/wsx-rootfs'
ROOT = Path(__file__).resolve().parents[1]
INDEX = 'graphics-sources.json'
ARCHIVES = ('graphics-notices.tar.gz', 'graphics-changes.tar.gz', 'graphics-retained-sources.tar.gz')
PROFILES = {
    'omarchy': {'mesa', 'venus', 'aquamarine', 'hyprland', 'udis86', 'glaze'},
    'cachyos-plasma': {'mesa', 'venus', 'kwin'},
}
REFERENCE_ONLY = {'aquamarine', 'hyprland', 'udis86', 'glaze'}
# Mesa has mixed per-file terms. Keep its pinned archives until a narrower
# compiled-source license review justifies reference-only delivery.
RETAIN_ARCHIVE = {'mesa', 'venus', 'kwin'}
PROJECTION_VERSION = 1


def canonical(document):
    return json.dumps(document, sort_keys=True, separators=(',', ':')).encode()


@contextmanager
def deterministic_tar(path):
    with path.open('wb') as raw, gzip.GzipFile(filename='', fileobj=raw, mode='wb', mtime=0) as compressed:
        with tarfile.open(fileobj=compressed, mode='w') as archive:
            yield archive


def add_bytes(archive, name, data, mode=0o644):
    relative(name)
    info = tarfile.TarInfo(name)
    info.size = len(data); info.mode = mode; info.mtime = 0
    archive.addfile(info, io.BytesIO(data))
    return dict(path=name, sha256=hashlib.sha256(data).hexdigest(), size=len(data), mode=mode)


def add_stream(archive, name, stream, size, digest, mode=0o644):
    relative(name)
    info = tarfile.TarInfo(name); info.size = size; info.mode = mode; info.mtime = 0
    archive.addfile(info, stream)
    return dict(path=name, sha256=digest, size=size, mode=mode)


def upstream_mode(component, profile):
    if profile not in PROFILES or component not in REFERENCE_ONLY | RETAIN_ARCHIVE:
        raise ValueError('Unreviewed source component/profile')
    if component not in PROFILES[profile]:
        return 'not-built-for-profile'
    return 'fixed-source-reference' if component in REFERENCE_ONLY else 'archive-retained'


def selection(name, profile, pins):
    """Only explicitly known expanded trees are omitted; new paths are retained."""
    relative(name)
    parts = name.split('/')
    if parts[0] == 'archives':
        if len(parts) != 2 or not parts[1].endswith('.archive'):
            raise ValueError('Unknown upstream archive path')
        component = parts[1][:-8]
        mode = upstream_mode(component, profile)
        return ('retained' if mode == 'archive-retained' else None), mode
    if name.startswith('rootfs-recipe/'):
        raise ValueError('Shared component package must not contain image-specific recipe material')
    if parts[0] == 'build-materials' and len(parts) >= 2:
        component = parts[1]
        if component in pins:
            if component not in PROFILES[profile]:
                return None, 'not-built-for-profile'
            if component == 'kwin':
                return 'retained', 'GPL preparation and build materials'
            pin = pins[component]
            tree = {'mesa': 'mesa-'+pin.get('version', ''), 'venus': 'mesa-'+pin.get('version', ''),
                    'hyprland': 'Hyprland-'+pin.get('commit', ''),
                    'aquamarine': 'aquamarine-'+pin.get('commit', ''),
                    'glaze': 'glaze-'+pin.get('commit', '')}.get(component)
            if len(parts) >= 3 and parts[2] == tree:
                return None, 'Expanded tree reconstructed from fixed input and retained original/adapted builders and patches'
    return 'changes', 'Original/adapted recipes, patches, generated definitions or build records'


def validate_index(index, receipt=None):
    if index.get('schema_version') != 1 or index.get('profile') not in PROFILES:
        raise ValueError('Unknown shared source index')
    unsigned = {k:v for k,v in index.items() if k not in ('bundle_id', 'tag')}
    if hashlib.sha256(canonical(unsigned)).hexdigest() != index.get('bundle_id'):
        raise ValueError('Shared source identity mismatch')
    expected_tag = 'graphics-sources-'+index['profile']+'-'+index['bundle_id'][:20]
    if index.get('tag') != expected_tag:
        raise ValueError('Shared source tag mismatch')
    if [f['name'] for f in index.get('files', [])] != list(ARCHIVES):
        raise ValueError('Shared source asset set mismatch')
    for f in index['files']:
        if not re.fullmatch(r'[0-9a-f]{64}', f.get('sha256', '')) or type(f.get('size')) is not int or f['size'] <= 0:
            raise ValueError('Invalid shared source asset digest/size')
    if receipt is not None and (receipt.get('profile') != index['profile'] or receipt != index.get('component_receipt')):
        raise ValueError('Shared source does not match the exact component receipt')
    return index


def make_bundle(work, output):
    material = verify(work)
    if material['schema_version'] == 2:
        # New compiler runs already produced the exact shared files directly.
        # Never rebuild a monolithic archive merely to project it again.
        shutil.copytree(work/'component-materials/shared',output)
        return verify_bundle(output)
    receipt = json.loads((work/'component-source.json').read_text())
    profile = receipt['profile']
    pins = json.loads((ROOT/'components/sources.json').read_text())
    if set(receipt['archives']) != set(pins)-{'schema_version'}:
        raise ValueError('Unreviewed upstream archive set')
    for component, original in receipt['archives'].items():
        if original['sha256'] != pins[component]['sha256']:
            raise ValueError('Pinned upstream inputs changed; review the projection first')
    expected = {r['path']:r for r in material['source_entries']}
    if len(expected) != len(material['source_entries']):
        raise ValueError('Duplicate original material index')
    output.mkdir(parents=True, exist_ok=False)
    entries = {name:[] for name in ARCHIVES}
    with deterministic_tar(output/ARCHIVES[0]) as notices:
        for name, digest in sorted(material['notice_files'].items()):
            path = work/'component-materials/notices'/name
            entries[ARCHIVES[0]].append(add_bytes(notices, 'notices/'+name, path.read_bytes()))
    omitted = []
    seen = set()
    with deterministic_tar(output/ARCHIVES[1]) as changes, deterministic_tar(output/ARCHIVES[2]) as retained:
        with tarfile.open(work/'component-materials/sources.tar', 'r:') as source:
            for member in source:
                if member.isdir():
                    continue
                name = member.name
                relative(name)
                if not member.isfile() or name in seen or name not in expected:
                    raise ValueError('Unexpected original material member: '+name)
                seen.add(name)
                row = expected[name]
                with source.extractfile(member) as stream:
                    digest = hashlib.file_digest(stream, 'sha256').hexdigest()
                if digest != row['sha256'] or member.size != row['size']:
                    raise ValueError('Original source member differs: '+name)
                if name.endswith('/distros/cachyos-plasma/upstream/netinstall.yaml'):
                    raise ValueError('Retired installer input in component material')
                destination, reason = selection(name, profile, pins)
                if destination is None:
                    omitted.append(dict(path=name, sha256=digest, size=member.size, reason=reason))
                    continue
                target = ARCHIVES[1] if destination == 'changes' else ARCHIVES[2]
                with source.extractfile(member) as stream:
                    entries[target].append(add_stream(changes if destination=='changes' else retained,
                        name, stream, member.size, digest, member.mode & 0o777))
        if seen != set(expected):
            raise ValueError('Original source members missing')
        # Retain a readable record of both inclusion policy and exact upstream pins.
        provenance = dict(profile=profile, component_receipt_sha256=material['source_receipt_sha256'],
            upstream={c:dict(pins[c], delivery=upstream_mode(c, profile)) for c in sorted(receipt['archives'])},
            modifications='See recipe/vendor, build-materials/builders and component-source.json; '
                          'the original compilation recipe and generated build records are retained.',
            licensing='Each file retains its applicable terms. No PolyForm overlay on upstream/GPL materials.')
        entries[ARCHIVES[1]].append(add_bytes(changes, 'SOURCE-ORIGINS.json', canonical(provenance)+b'\n'))
    index = dict(schema_version=1, projection_version=PROJECTION_VERSION, profile=profile,
        component_receipt=receipt, source_receipt_sha256=material['source_receipt_sha256'],
        original_material_sha256=sha(work/'component-materials/materials.json'),
        original_sources=material['sources'], upstream=provenance['upstream'],
        files=[dict(name=n, sha256=sha(output/n), size=(output/n).stat().st_size, entries=entries[n]) for n in ARCHIVES],
        omitted_entries=omitted, corresponding_source_complete=False,
        scope='Shared graphics notices, modifications/build materials and conservatively retained upstream sources; '
              'no full-rootfs system package source completeness claim')
    index['bundle_id'] = hashlib.sha256(canonical(index)).hexdigest()
    index['tag'] = 'graphics-sources-'+profile+'-'+index['bundle_id'][:20]
    validate_index(index, receipt)
    (output/INDEX).write_text(json.dumps(index, indent=2)+'\n')
    verify_bundle(output)
    return index


def verify_bundle(directory):
    index = validate_index(json.loads((directory/INDEX).read_text()))
    if {p.name for p in directory.iterdir()} != set(ARCHIVES) | {INDEX}:
        raise ValueError('Unexpected shared source files')
    for item in index['files']:
        path = directory/item['name']
        if path.is_symlink() or sha(path) != item['sha256'] or path.stat().st_size != item['size']:
            raise ValueError('Shared source archive changed')
        expected = {r['path']:r for r in item['entries']}
        if len(expected) != len(item['entries']):
            raise ValueError('Duplicate shared source index entry')
        seen = set()
        with tarfile.open(path, 'r:gz') as archive:
            for member in archive:
                relative(member.name)
                if not member.isfile() or member.name in seen or member.name not in expected:
                    raise ValueError('Unsafe or unindexed shared source member')
                seen.add(member.name)
                row = expected[member.name]
                with archive.extractfile(member) as stream:
                    digest = hashlib.file_digest(stream, 'sha256').hexdigest()
                if digest != row['sha256'] or member.size != row['size'] or member.mode != row['mode']:
                    raise ValueError('Shared source member mismatch')
        if seen != set(expected):
            raise ValueError('Missing shared source entries')
    return index


def pin_for(root, profile):
    config = json.loads((root/'components/source-delivery.json').read_text())
    if config.get('schema_version') != 1 or config.get('mode') != 'shared-v2':
        raise ValueError('Unknown source delivery configuration')
    pin = config['profiles'].get(profile)
    if not isinstance(pin, dict):
        raise ValueError('No publicly available shared source pin for '+profile+'; prepare and publish its source-only bundle')
    validate_pin(pin, profile)
    return pin


def validate_pin(pin, profile):
    if not re.fullmatch(r'graphics-sources-'+re.escape(profile)+r'-[0-9a-f]{20}', pin.get('tag','')):
        raise ValueError('Unexpected shared source release tag')
    if not re.fullmatch(r'[0-9a-f]{64}', pin.get('manifest_sha256','')):
        raise ValueError('Invalid shared source manifest hash')


def public_json(url):
    # No credentials: a private/Draft source bundle cannot satisfy public delivery.
    with urlopen(Request(url, headers={'User-Agent':'WSX-source-delivery/2'}), timeout=60) as response:
        return json.loads(response.read(16*1024*1024))


def _verify_release(pin, index, read_metadata, private):
    validate_index(index)
    validate_pin(pin, index['profile'])
    if pin['tag'] != index['tag']:
        raise ValueError('Shared source release differs from pinned index')
    repo = read_metadata('https://api.github.com/repos/'+REPOSITORY)
    release = read_metadata('https://api.github.com/repos/'+REPOSITORY+'/releases/tags/'+pin['tag'])
    if repo.get('full_name') != REPOSITORY or repo.get('private') is not private or release.get('draft') is not False:
        raise ValueError('Shared source must be publicly accessible' if not private else 'Shared source must be an accessible private release')
    if release.get('tag_name') != pin['tag']:
        raise ValueError('Shared source release identity mismatch')
    asset_list = release.get('assets', [])
    assets = {a['name']:a for a in asset_list}
    if len(assets) != len(asset_list):
        raise ValueError('Duplicate shared source asset names')
    records = list(index['files']) + [dict(name=INDEX, sha256=pin['manifest_sha256'])]
    for record in records:
        asset = assets.get(record['name'], {})
        url = f'https://github.com/{REPOSITORY}/releases/download/{pin["tag"]}/{record["name"]}'
        if (asset.get('browser_download_url') != url or asset.get('state') != 'uploaded'
                or asset.get('digest') != 'sha256:'+record['sha256']
                or ('size' in record and asset.get('size') != record['size'])):
            raise ValueError('Public shared source asset missing or changed: '+record['name'])
    return release


def verify_public(pin, index, metadata_reader=None):
    return _verify_release(pin, index, metadata_reader or public_json, False)


def private_json(url):
    prefix = 'https://api.github.com/'
    if not url.startswith(prefix) or not os.environ.get('GH_TOKEN'):
        raise ValueError('Authenticated private source access requires GH_TOKEN')
    return json.loads(subprocess.check_output(['gh', 'api', url[len(prefix):]]))


def verify_private(pin, index, metadata_reader=None):
    return _verify_release(pin, index, metadata_reader or private_json, True)


def download_index(pin, profile):
    validate_pin(pin, profile)
    if os.environ.get('WSX_PRIVATE_SOURCE') == '1':
        repo = private_json('https://api.github.com/repos/' + REPOSITORY)
        if repo.get('full_name') != REPOSITORY or repo.get('private') is not True:
            raise ValueError('Private source mode requires the approved private repository')
        release = private_json('https://api.github.com/repos/' + REPOSITORY + '/releases/tags/' + pin['tag'])
        matches = [a for a in release.get('assets', []) if a.get('name') == INDEX]
        if release.get('draft') is not False or len(matches) != 1 or type(matches[0].get('id')) is not int:
            raise ValueError('Private source index asset is missing or ambiguous')
        data = subprocess.check_output(['gh', 'api', '-H', 'Accept: application/octet-stream',
                                        f'repos/{REPOSITORY}/releases/assets/{matches[0]["id"]}'])
        if len(data) > 16*1024*1024:
            raise ValueError('Private source index exceeds size limit')
    else:
        url = f'https://github.com/{REPOSITORY}/releases/download/{pin["tag"]}/{INDEX}'
        with urlopen(Request(url,headers={'User-Agent':'WSX-source-delivery/2'}),timeout=60) as stream:
            data = stream.read(16*1024*1024)
    if hashlib.sha256(data).hexdigest() != pin['manifest_sha256']:
        raise ValueError('Public shared source index hash mismatch')
    index = validate_index(json.loads(data))
    (verify_private if os.environ.get('WSX_PRIVATE_SOURCE') == '1' else verify_public)(pin, index)
    return data
