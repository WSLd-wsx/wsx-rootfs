"""Retain source/build materials and notices without asserting legal clearance."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import tarfile
import time
from product_licenses import write_component_map

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def relative(name):
    path = PurePosixPath(name)
    if not path.parts or path.is_absolute() or '..' in path.parts or str(path) != name:
        raise ValueError('Unsafe material path: ' + name)
    return path


def notice_candidate(name):
    parts = PurePosixPath(name).parts
    return any(part.lower() in ('licenses', 'licences') for part in parts) or parts[-1].lower().startswith(
        ('license', 'licence', 'copying', 'notice', 'copyright', 'authors'))


def prepare_legacy(work):
    work = work.resolve(strict=True)
    receipt = json.loads((work/'component-source.json').read_text())
    if receipt.get('origin') != 'source-build' or receipt.get('compiled') is not True:
        raise ValueError('Completed source receipt required for material collection')
    output = work/'component-materials'
    output.mkdir(exist_ok=False)
    notices = output/'notices'; notices.mkdir()
    entries = []; collected = []; started = time.monotonic()
    source = output/'sources.tar'
    with tarfile.open(source, 'w') as tar:
        def add(path, name):
            relative(name)
            if path.is_symlink():
                raise ValueError('Recipe material symlink requires review: ' + str(path))
            if not path.is_file():
                raise ValueError('Missing source material: ' + str(path))
            tar.add(path, arcname=name, recursive=False)
            entries.append(dict(path=name, sha256=sha(path), size=path.stat().st_size))
        for component, pin in sorted(receipt['archives'].items()):
            relative(component)
            archive = work/'source-archives'/(component+'.archive')
            if sha(archive) != pin['sha256']:
                raise ValueError('Source archive changed: ' + component)
            add(archive, 'archives/'+component+'.archive')
            # Names identify notice candidates only; the complete archive is retained.
            with tarfile.open(archive) as upstream:
                for member in upstream:
                    if not member.isfile() or not notice_candidate(member.name):
                        continue
                    name = str(relative(member.name))
                    target = notices/'upstream'/component/name
                    if target.exists():
                        raise ValueError('Duplicate upstream notice path')
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with upstream.extractfile(member) as src, target.open('wb') as dst:
                        shutil.copyfileobj(src, dst)
                    collected.append(dict(component=component, archive_sha256=pin['sha256'],
                                          source_path=name, notice_path=str(target.relative_to(notices)),
                                          sha256=sha(target), classification='notice-candidate-not-license-conclusion'))
        for name, digest in sorted(receipt['recipe_files'].items()):
            relative(name)
            path = ROOT/name
            if sha(path) != digest:
                raise ValueError('Recipe changed after build: ' + name)
            add(path, 'recipe/'+name)
        # Retain adapted builders, patched trees and generated source definitions.
        # Exclude installed binaries, object files and build-system caches.
        build = work/'component-build'
        for path in sorted(build.rglob('*')):
            local = path.relative_to(build)
            if '__pycache__' in local.parts or path.is_dir():
                continue
            if any(part in ('prefix', 'stage', 'candidate', 'upstream') for part in local.parts):
                continue
            if 'build' in local.parts and path.suffix.lower() not in ('.h','.hpp','.c','.cpp','.xml','.qml','.py','.sh','.cmake','.json','.txt','.ninja'):
                continue
            if path.is_symlink():
                # Archive inputs preserve upstream link metadata; do not follow links
                # out of a compiler tree or silently import unrelated host files.
                if not path.resolve(strict=True).is_relative_to(build):
                    raise ValueError('Build material link escapes workspace')
                continue
            if path.is_file():
                add(path, 'build-materials/'+str(local))
        add(work/'component-source.json', 'component-source.json')
        for name in ('build-packages.txt','build-repositories.conf'):
            add(work/name, 'environment/'+name)
    write_component_map(ROOT, receipt, notices)
    references = ROOT/'docs/licensing/licenses'
    shutil.copytree(references, notices/'reference-texts')
    # Keep original declarations as source evidence, without inventing holders.
    shutil.copytree(ROOT/'vendor', notices/'vendored-source', ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    (notices/'README.txt').write_text(
        'NOTICE MATERIALS — REVIEW REQUIRED\n'
        'Original declarations and reference texts are retained. Files selected by name\n'
        'are notice candidates, not automatic license determinations. No blanket WSX\n'
        'license applies to upstream software. Active grants have explicit module scope.\n'
        'The source material archive includes pinned archives, original/adapted recipes,\n'
        'patched trees and selected generated definitions. Full dependency closure and\n'
        'image-wide notices still need review; public distribution is not approved.\n')
    (notices/'upstream-index.json').write_text(json.dumps(collected,indent=2)+'\n')
    with tarfile.open(source, 'a') as archive:
        for name in ('MODULE-LICENSES.json', 'MODULE-NOTICES.txt'):
            archive.add(notices/name, arcname='licensing/'+name, recursive=False)
            entries.append(dict(path='licensing/'+name, sha256=sha(notices/name), size=(notices/name).stat().st_size))
    report = dict(schema_version=1, profile=receipt.get('profile','omarchy'),
        source_receipt_sha256=sha(work/'component-source.json'),
        sources=dict(path='sources.tar',sha256=sha(source),size=source.stat().st_size),
        source_entries=entries, notice_files={str(p.relative_to(notices)):sha(p) for p in sorted(notices.rglob('*')) if p.is_file()},
        collection_complete=True, license_review='pending', corresponding_source_complete=False,
        distribution_allowed=False, elapsed_seconds=round(time.monotonic()-started,3),
        exclusions=['installed binary prefixes','object files','non-source compiler caches','non-vendored dependency sources'],
        scope='Build/source evidence package; legal corresponding-source completeness is not asserted')
    (output/'materials.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def verify_legacy(work):
    directory = work/'component-materials'
    report = json.loads((directory/'materials.json').read_text())
    if report.get('schema_version') != 1 or report.get('collection_complete') is not True:
        raise ValueError('Source material collection incomplete')
    if report['source_receipt_sha256'] != sha(work/'component-source.json'):
        raise ValueError('Material receipt does not match runtime receipt')
    if report['sources']['path'] != 'sources.tar':
        raise ValueError('Unexpected source material archive path')
    archive = directory/'sources.tar'
    if sha(archive) != report['sources']['sha256'] or archive.stat().st_size != report['sources']['size']:
        raise ValueError('Source material archive changed')
    if any(p.is_symlink() for p in directory.rglob('*')):
        raise ValueError('Material symlinks are not allowed')
    actual={str(p.relative_to(directory/'notices')):sha(p) for p in (directory/'notices').rglob('*') if p.is_file()}
    if not actual or actual != report['notice_files']:
        raise ValueError('Notice materials changed')
    return report


def prepare(work):
    """Collect compact sources directly; legacy collection is test/history only."""
    from compact_materials import prepare as compact_prepare
    return compact_prepare(work)


def source_files(report):
    if report.get('schema_version') == 1:
        return {'sources.tar': 'sources.tar'}
    if report.get('schema_version') == 2:
        from shared_sources import ARCHIVES, INDEX
        return {name: 'shared/'+name for name in (*ARCHIVES, INDEX)}
    raise ValueError('Unknown component source material format')


def source_descriptor(report):
    return report['sources'] if report['schema_version'] == 1 else report['source_bundle']


def verify(work):
    report = json.loads((work/'component-materials/materials.json').read_text())
    if report.get('schema_version') == 1:
        return verify_legacy(work)
    if report.get('schema_version') == 2:
        from compact_materials import verify as compact_verify
        return compact_verify(work)
    raise ValueError('Unknown component source material format')
