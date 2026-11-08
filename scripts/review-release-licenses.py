#!/usr/bin/env python3
"""Read release archives without extraction; report evidence, never legal approval."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import tarfile
import shutil
import os
import tempfile
from urllib.request import Request, urlopen
from payload_contract import validate_completion
from source_delivery import required_assets
import shared_sources


def upstream_text_candidate(name):
    path = PurePosixPath(name)
    return (name.startswith('usr/share/omarchy/') and
            path.suffix.lower() in ('', '.txt', '.md', '.rst', '.html') and
            path.name.lower().startswith(('license', 'copying', 'copyright', 'notice', 'ofl', 'readme', 'credits', 'authors')))


def pacman_fields(data):
    fields = {}
    key = None
    for line in data.decode('utf-8').splitlines():
        if line.startswith('%') and line.endswith('%'):
            key = line[1:-1]
            if key in fields:
                raise ValueError('Duplicate pacman field: ' + key)
            fields[key] = []
        elif line and key:
            fields[key].append(line)
    return fields


def whole_image_evidence(hashes, links, texts):
    packages = []
    for path, data in sorted(texts.items()):
        if not path.startswith('var/lib/pacman/local/') or not path.endswith('/desc'):
            continue
        desc = pacman_fields(data)
        listing = pacman_fields(texts[path.rsplit('/', 1)[0]+'/files']).get('FILES', [])
        owned_notices = [p for p in listing if p.startswith('usr/share/licenses/') and not p.endswith('/')]
        packages.append(dict(name=desc['NAME'][0], version=desc['VERSION'][0],
                             url=desc.get('URL', []), declared_licenses=desc.get('LICENSE', []),
                             depends=desc.get('DEPENDS', []), provides=desc.get('PROVIDES', []),
                             owned_notices=[dict(path=p, sha256=hashes.get(p), link=links.get(p)) for p in owned_notices],
                             missing_owned_notices=[p for p in owned_notices if p not in hashes and p not in links]))
    notice_texts = {p: dict(sha256=hashes[p], text=data.decode('utf-8', errors='replace'))
                    for p, data in sorted(texts.items())
                    if p.startswith('usr/share/licenses/') and not p.startswith('usr/share/licenses/wsx-components/')}
    fonts = {}
    for path, data in texts.items():
        if not path.startswith('usr/share/fonts/omarchy/') or not path.endswith('.ttf'):
            continue
        import io
        from fontTools.ttLib import TTFont
        with TTFont(io.BytesIO(data)) as font:
            fonts[path] = dict(sha256=hashes[path], names=[
                dict(name_id=n.nameID, text=n.toUnicode()) for n in font['name'].names
                if n.nameID in (0, 1, 2, 4, 7, 8, 9, 11, 13, 14)])
    return dict(packages=packages, notice_texts=notice_texts, font_metadata=fonts,
                scope='Actual package metadata, owned notice paths, retained notice bytes and embedded font name records; no inferred legal clearance')


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def members(stream):
    hashes, links, texts, sizes = {}, {}, {}, {}
    seen = set()
    with tarfile.open(fileobj=stream, mode='r|') as archive:
        for member in archive:
            name = member.name.removeprefix('./').rstrip('/')
            if not name or name == '.':
                continue
            if PurePosixPath(name).is_absolute() or '..' in PurePosixPath(name).parts:
                raise ValueError('Unsafe archive name: ' + name)
            if name in seen:
                raise ValueError('Duplicate archive entry: ' + name)
            seen.add(name)
            if member.isfile():
                content = archive.extractfile(member)
                capture = (name.startswith('usr/share/licenses/') or
                           upstream_text_candidate(name) or
                           (name.startswith('usr/share/fonts/omarchy/') and name.endswith('.ttf')) or
                           (name.startswith('var/lib/pacman/local/') and
                            name.rsplit('/', 1)[-1] in ('desc', 'files')))
                if capture and member.size > 32 * 1024 * 1024:
                    raise ValueError('Oversized notice/metadata: ' + name)
                if capture:
                    data = content.read()
                    hashes[name] = hashlib.sha256(data).hexdigest()
                    texts[name] = data
                else:
                    hashes[name] = hashlib.file_digest(content, 'sha256').hexdigest()
                sizes[name] = member.size
            elif member.issym() or member.islnk():
                links[name] = dict(target=member.linkname, hard=member.islnk())
    # Hardlinks identify identical file bytes, not a second extracted payload.
    pending = {n: v for n, v in links.items() if v['hard']}
    while pending:
        progressed = False
        for name, link in list(pending.items()):
            target = link['target'].removeprefix('./')
            if target in hashes:
                hashes[name] = hashes[target]
                sizes[name] = sizes[target]
                if target in texts:
                    texts[name] = texts[target]
                del pending[name]
                progressed = True
        if not progressed:
            raise ValueError('Unresolved archive hardlinks')
    return hashes, links, texts, sizes


def require(condition, message):
    if not condition:
        raise ValueError(message)


def fetch_shared(pin, index, destination):
    """Fetch only verified public source assets; never require package credentials."""
    if 'image' in pin:
        auth, layers = shared_sources.registry_layers(pin, index)
        for row in index['files']:
            with (destination/row['name']).open('wb') as output:
                shared_sources.shared_registry.fetch(auth, layers[row['name']], output)
        return
    def metadata(url):
        # Authenticated metadata avoids shared-runner anonymous API rate limits.
        # Visibility is checked independently; asset downloads below stay anonymous.
        return json.loads(subprocess.check_output(['gh','api',url],text=True))
    shared_sources.verify_public(pin,index,metadata_reader=metadata if os.environ.get('GH_TOKEN') else None)
    for row in index['files']:
        url=f'https://github.com/{shared_sources.REPOSITORY}/releases/download/{pin["tag"]}/{row["name"]}'
        with urlopen(Request(url,headers={'User-Agent':'WSX-license-review'}),timeout=120) as stream:
            with (destination/row['name']).open('wb') as output:
                shutil.copyfileobj(stream,output)


def check_profile_sources(index, manifest):
    profiles={'wsx-omarchy':'omarchy','wsx-cachyos-plasma':'cachyos-plasma'}
    require(index['profile']==profiles.get(manifest['distribution_id']), 'Image/shared source profile mismatch')
    if index['profile']!='cachyos-plasma':
        return
    retained={r['path']:r for f in index['files'] for r in f['entries']}
    expected=index['component_receipt']['archives']['kwin']['sha256']
    require(retained.get('archives/kwin.archive',{}).get('sha256')==expected, 'KWin original source archive missing or mismatched')
    require(any(n.startswith('build-materials/kwin/') for n in retained), 'KWin prepared source/build materials missing')
    require(any(n.startswith('notices/upstream/kwin/') for n in retained), 'KWin upstream notices missing')


def source_evidence(directory, source, manifest):
    required_assets(directory,source)
    if manifest.get('source_delivery_schema',1)==1:
        materials=json.loads((directory/'component-materials.json').read_text())
        with (directory/'component-sources.tar').open('rb') as stream:
            hashes,_,_,sizes=members(stream)
        expected={r['path']:r for r in materials['source_entries']}
        require(set(hashes)==set(expected),'Source inventory coverage mismatch')
        for name,row in expected.items():
            require(hashes[name]==row['sha256'] and sizes[name]==row['size'],'Source entry mismatch: '+name)
        return materials,hashes,dict(schema_version=1)
    require(manifest.get('source_delivery_schema')==2,'Unsupported release source schema')
    delivery=source['component_source_delivery']
    pin=delivery['shared_source']
    index=json.loads((directory/'graphics-sources.json').read_text())
    check_profile_sources(index,manifest)
    with tempfile.TemporaryDirectory(prefix='wsx-shared-review-') as temporary:
        bundle=Path(temporary)
        shutil.copy2(directory/'graphics-sources.json',bundle/shared_sources.INDEX)
        fetch_shared(pin,index,bundle)
        shared_sources.verify_bundle(bundle)
    hashes={r['path']:r['sha256'] for f in index['files'] for r in f['entries']}
    hashes.update({r['path']:r['sha256'] for r in delivery['recipe_entries']})
    notices={r['path'].removeprefix('notices/'):r['sha256'] for r in index['files'][0]['entries']}
    materials=dict(notice_files=notices,license_review='evidence checked; legal conclusions remain scoped',
                   distribution_allowed=None,corresponding_source_complete=False)
    return materials,hashes,dict(schema_version=2,tag=pin['tag'],index_sha256=pin['manifest_sha256'],
        shared_archive_bytes=sum(f['size'] for f in index['files']),public_source_assets_verified=True,
        component_receipt_sha256=index['source_receipt_sha256'],
        components={c:dict(delivery=v['delivery'],url=v.get('url'),sha256=v.get('sha256')) for c,v in index['upstream'].items()})


def expected_image_notices(directory, source, original):
    """Bind updated image notices to validated recipe entries, preserving old evidence."""
    expected=dict(original)
    delivery=source.get('component_source_delivery',{})
    records={r['path']:r for r in delivery.get('recipe_entries',[])}
    base='rootfs-recipe/image-materials/component-materials/notices/'
    names=('MODULE-LICENSES.json','MODULE-NOTICES.txt')
    found=[base+n in records for n in names]
    if any(found) and not all(found):
        raise ValueError('Incomplete regenerated image notice inventory')
    if all(found):
        # required_assets already verified every recipe entry and its archive bytes.
        for name in names:
            expected[name]=records[base+name]['sha256']
        image_policy={'LICENSE':'rootfs-recipe/LICENSE',
                      'LICENSE-MAP.md':'rootfs-recipe/LICENSE-MAP.md',
                      'OUTPUT-LICENSES.md':'rootfs-recipe/docs/licensing/OUTPUT-LICENSES.md',
                      'PRIVATE-ARTIFACTS.md':'rootfs-recipe/docs/licensing/PRIVATE-ARTIFACTS.md'}
        for name,path in image_policy.items():
            if name in original:
                if path not in records:
                    raise ValueError('Missing regenerated image policy: '+name)
                expected[name]=records[path]['sha256']
    return expected


def review(directory):
    completion = json.loads((directory/'completion.json').read_text())
    for name, record in completion['assets'].items():
        require(Path(name).name == name, 'Unsafe asset name')
        path = directory/name
        require(path.stat().st_size == record['size'] and digest(path) == record['sha256'],
                'Release asset mismatch: ' + name)
    manifest = json.loads((directory/'manifest.json').read_text())
    source = json.loads((directory/'sources.json').read_text())
    validate_completion(manifest,completion)
    materials,source_hashes,source_details=source_evidence(directory,source,manifest)
    require(manifest['build_identity'] == completion['build_identity'], 'Identity mismatch')
    image = directory/manifest['asset_name']
    require(digest(image) == manifest['sha256'], 'Manifest image digest mismatch')
    process = subprocess.Popen(['zstd', '-dc', str(image)], stdout=subprocess.PIPE)
    try:
        hashes, links, texts, sizes = members(process.stdout)
        # Drain the decoder so corrupt trailing compressed data also fails.
        while process.stdout.read(1024 * 1024):
            pass
    finally:
        process.stdout.close()
        status = process.wait()
    require(status == 0, 'Image decompression failed')
    prefix = 'usr/share/licenses/wsx-components/'
    image_map = json.loads(texts[prefix+'IMAGE-LICENSES.json'])
    module_map = json.loads(texts[prefix+'MODULE-LICENSES.json'])
    require(image_map['module_map_sha256'] == hashes[prefix+'MODULE-LICENSES.json'],
            'Image/module map mismatch')
    require(image_map['license_grant'] is True and module_map['license_grant'] is True,
            'Expected active module grants')
    image_notices=expected_image_notices(directory,source,materials['notice_files'])
    for name, expected in image_notices.items():
        require(hashes.get(prefix+name) == expected, 'Notice mismatch: ' + name)
    for row in image_map['files']:
        if 'sha256' in row:
            require(hashes.get(row['path']) == row['sha256'], 'Mapped output mismatch: '+row['path'])
        else:
            require(links.get(row['path'], {}).get('target') == row['symlink'],
                    'Mapped link mismatch: '+row['path'])
    evidence = image_map['package_evidence']
    for package in evidence['packages']:
        for row in package['metadata']:
            require(hashes.get(row['path']) == row['sha256'], 'Package metadata mismatch')
    for row in evidence['installed_license_files']:
        if 'sha256' in row:
            require(hashes.get(row['path']) == row['sha256'], 'System notice mismatch')
        else:
            require(links.get(row['path'], {}).get('target') == row['symlink'], 'Notice link mismatch')
    installed = {p['name']: p['version'] for p in evidence['packages']}
    require(installed == dict(line.split(' ', 1) for line in source['rootfs_packages']),
            'Installed package list differs from sources.json')
    retired = '9f29e5ea796a30b43c1e4a1367960694fb2a620fd88c2911795b4e9460143486'
    require(retired not in source_hashes.values() and retired not in hashes.values(),
            'Retired upstream file included')
    packages = [dict(name=p['name'], version=p['version'], declared_licenses=p['declared_licenses'])
                for p in evidence['packages']]
    report = dict(
        schema_version=1, distribution_id=manifest['distribution_id'], image_version=manifest['image_version'], build_commit=manifest['build_commit'],
        archive_sha256=manifest['sha256'], all_completion_asset_hashes_match=True,
        image_module_bindings_match=True, component_notice_files=len(materials['notice_files']),
        mapped_image_files=len(image_map['files']), system_notice_entries=len(evidence['installed_license_files']),
        source_entries_verified=len(source_hashes), source_delivery=source_details, retired_file_present=False,
        outputs=[dict(id=o['id'], treatment=o['license_treatment']) for o in module_map['outputs']],
        unmanaged_upstream_notices={n: data.decode('utf-8', errors='replace')
            for n, data in texts.items() if n.startswith('usr/share/omarchy/')},
        unmanaged_resource_paths=[n for n in hashes if n.startswith(('usr/share/omarchy/themes/',
            'usr/share/omarchy/default/fonts/', 'usr/share/fonts/omarchy/'))],
        unmanaged_resource_hashes={n: h for n, h in hashes.items() if n.startswith(('usr/share/omarchy/themes/',
            'usr/share/omarchy/default/fonts/', 'usr/share/fonts/omarchy/'))},
        whole_image_evidence=whole_image_evidence(hashes, links, texts),
        packages=packages, packages_without_license_declaration=[p for p in packages if not p['declared_licenses']],
        declared_legal_status={k:materials[k] for k in ('license_review','distribution_allowed','corresponding_source_complete')},
        public_distribution_approved=False,
        limitations=['Package license declarations are evidence, not permission conclusions.',
                     'Unmanaged assets, complete system-package source delivery and trademark rights need separate review.',
                     'Archive checks do not establish hardware acceptance.'])
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('report', type=Path)
    args = parser.parse_args()
    result = review(args.directory)
    args.report.write_text(json.dumps(result, indent=2)+'\n')
    # Short chunks survive log line limits when artifact storage is unavailable.
    import base64
    payload = base64.b64encode(args.report.read_bytes()).decode('ascii')
    for offset in range(0, len(payload), 2000):
        print('LICENSE_REVIEW_CHUNK ' + payload[offset:offset+2000])
    print('LICENSE_REVIEW_SHA256 ' + digest(args.report))
