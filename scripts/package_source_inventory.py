"""Record installed package source-discovery evidence without implying clearance."""
import hashlib
from pathlib import Path
import re
from urllib.parse import quote

NAME = re.compile(r'[a-zA-Z0-9@._+:~-]+\Z')


def fields(data):
    result = {}; current = None
    for line in data.decode('utf-8').splitlines():
        if line.startswith('%') and line.endswith('%'):
            current = line[1:-1]
            if current in result:
                raise ValueError('Duplicate package metadata field')
            result[current] = []
        elif line and current is not None:
            result[current].append(line)
    return result


def create(rootfs, expected, repository_versions):
    rootfs = Path(rootfs).resolve(strict=True)
    database = rootfs / 'var/lib/pacman/local'
    if database.is_symlink() or not database.is_dir() or not database.resolve().is_relative_to(rootfs):
        raise ValueError('Missing or unsafe installed package database')
    repositories = {}
    for line in repository_versions:
        parts = line.split()
        if len(parts) >= 3 and NAME.fullmatch(parts[0]) and NAME.fullmatch(parts[1]):
            repositories.setdefault((parts[1], parts[2]), set()).add(parts[0])
    rows = []; identities = set()
    for directory in sorted(database.iterdir()):
        if directory.name == 'ALPM_DB_VERSION' and directory.is_file() and not directory.is_symlink():
            continue
        if directory.is_symlink() or not directory.is_dir():
            raise ValueError('Unsafe package database entry')
        desc = directory / 'desc'; listing = directory / 'files'
        for path in (desc, listing):
            if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(rootfs):
                raise ValueError('Unsafe installed package metadata')
        raw = desc.read_bytes(); meta = fields(raw)
        if len(meta.get('NAME', [])) != 1 or len(meta.get('VERSION', [])) != 1:
            raise ValueError('Invalid installed package identity')
        name, version = meta['NAME'][0], meta['VERSION'][0]
        if not NAME.fullmatch(name) or not NAME.fullmatch(version) or name in identities:
            raise ValueError('Unsafe or duplicate installed package identity')
        identities.add(name)
        base_values = meta.get('BASE', [])
        if len(base_values) > 1 or (base_values and not NAME.fullmatch(base_values[0])):
            raise ValueError('Invalid package base')
        base = base_values[0] if base_values else None
        repos = sorted(repositories.get((name, version), set()))
        candidates = []
        if base and any(repo in ('core', 'extra', 'multilib') for repo in repos):
            candidates.append({'kind': 'arch-packaging-history',
                'url': 'https://gitlab.archlinux.org/archlinux/packaging/packages/' + quote(base, safe='') + '/',
                'status': 'discovery_only'})
        for url in meta.get('URL', []):
            if url.startswith(('https://', 'http://')) and not any(ch.isspace() for ch in url):
                candidates.append({'kind': 'upstream-homepage', 'url': url, 'status': 'discovery_only'})
        rows.append({'name': name, 'version': version, 'package_base': base,
            'repositories_observed': repos, 'declared_licenses': meta.get('LICENSE', []),
            'upstream_urls': meta.get('URL', []), 'build_date': meta.get('BUILDDATE', []),
            'description_sha256': hashlib.sha256(raw).hexdigest(),
            'file_list_sha256': hashlib.sha256(listing.read_bytes()).hexdigest(),
            'source_candidates': candidates, 'source_correspondence': 'not_verified'})
    if {row['name'] + ' ' + row['version'] for row in rows} != set(expected):
        raise ValueError('Installed package inventory differs from recorded package list')
    return {'schema_version': 1, 'packages': rows, 'source_completeness': 'not_verified',
            'scope': 'Installed metadata and discovery links only; neither exact source availability nor legal completeness is established.'}

# This exact x86-64 Arch package was checked against its binary, .BUILDINFO,
# PKGBUILD and source tag. Other versions or changed binaries remain unresolved.
FDK = {'version': '3.0.0-1',
       'library': 'usr/lib/libfdk-aac.so.2.0.4',
       'library_sha256': '0f2d70bd65d447d87def544d54cacd93ad9e61fd5cbf9dbf3cf76aaa9e1ea352',
       'notice': 'usr/share/licenses/libfdk-aac/NOTICE',
       'notice_sha256': '95ec80da40b4af12ad4c4f3158c9cfb80f2479f3246e4260cb600827cc8c7836',
       'sources': (
           ('fdk-aac-source.tar.gz',
            'https://codeload.github.com/mstorsjo/fdk-aac/tar.gz/a68a51aa45d86a43c7b228e3d45624af09dcdd8d',
            'ac9682b35f6e5f75e1f008a5ba2636ba6c9c77c70b78377b53992559e8bda806'),
           ('arch-libfdk-aac-packaging.tar.gz',
            'https://gitlab.archlinux.org/archlinux/packaging/packages/libfdk-aac/-/archive/b0c45e29a1bac452ece793799738e066d0c3f2cb/libfdk-aac-b0c45e29a1bac452ece793799738e066d0c3f2cb.tar.gz',
            'c592996155069f4e7d290178a4ac1d9a914dbd13f3c7e8246de0a19086a4b2d4'))}


def collect_known_sources(rootfs, inventory, work):
    """Retain known exact-version source where possible; unavailable is not clearance."""
    import json
    import shutil
    import tempfile
    from urllib.request import Request, urlopen

    matches = [x for x in inventory['packages'] if x['name'] == 'libfdk-aac']
    if not matches:
        return
    row = matches[0]
    row['retained_source_status'] = 'not_collected'
    row.pop('retained_source_manifest', None)
    if row['version'] != FDK['version']:
        return
    rootfs = Path(rootfs).resolve(strict=True)
    for key in ('library', 'notice'):
        path = rootfs / FDK[key]
        if (path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(rootfs)
                or hashlib.sha256(path.read_bytes()).hexdigest() != FDK[key + '_sha256']):
            row['retained_source_status'] = 'binary_or_notice_not_matched'
            return
    destination = Path(work) / 'package-source-evidence'
    if destination.exists() or destination.is_symlink():
        raise ValueError('Package source evidence destination already exists')
    try:
        with tempfile.TemporaryDirectory(prefix='wsx-package-source-', dir=work) as temporary:
            temp = Path(temporary); records = []
            for name, url, expected in FDK['sources']:
                if not re.fullmatch(r'[a-z0-9.-]+\.tar\.gz', name):
                    raise ValueError('Invalid fixed source name')
                with urlopen(Request(url, headers={'User-Agent': 'WSX-source-evidence'}), timeout=30) as response:
                    data = response.read(16 * 1024 * 1024 + 1)
                if len(data) > 16 * 1024 * 1024 or hashlib.sha256(data).hexdigest() != expected:
                    raise ValueError('Fixed source archive hash differs')
                (temp / name).write_bytes(data)
                records.append({'name': name, 'url': url, 'sha256': expected, 'size': len(data)})
            receipt = {'schema_version': 1, 'package': 'libfdk-aac', 'version': FDK['version'],
                       'binary_path': FDK['library'], 'binary_sha256': FDK['library_sha256'],
                       'notice_sha256': FDK['notice_sha256'], 'files': records,
                       'scope': 'Fixed upstream and Arch packaging source for a matching library; no reproducible build, patent or whole-image license conclusion.'}
            (temp / 'manifest.json').write_text(json.dumps(receipt, sort_keys=True, indent=2) + '\n')
            destination.mkdir()
            for path in temp.iterdir():
                shutil.copyfile(path, destination / path.name)
        row['retained_source_status'] = 'matching_library_source_retained'
        row['retained_source_manifest'] = 'rootfs-recipe/package-source-evidence/manifest.json'
    except (OSError, ValueError):
        if destination.exists():
            shutil.rmtree(destination)
        row['retained_source_status'] = 'unavailable_or_hash_mismatch'
