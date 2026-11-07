"""Collect compact source-only archives directly from a completed compiler run."""
import hashlib
import json
from pathlib import Path
import shutil
import tarfile
import time

from component_materials import sha, relative, notice_candidate
from product_licenses import write_component_map
from shared_sources import (ARCHIVES, INDEX, PROJECTION_VERSION, canonical, selection,
    upstream_mode, deterministic_tar, add_stream, add_bytes, validate_index, verify_bundle)

ROOT = Path(__file__).resolve().parents[1]


def prepare(work):
    work = work.resolve(strict=True)
    receipt = json.loads((work/'component-source.json').read_text())
    if receipt.get('origin') != 'source-build' or receipt.get('compiled') is not True:
        raise ValueError('Completed source receipt required for compact collection')
    profile = receipt['profile']
    pins = json.loads((ROOT/'components/sources.json').read_text())
    if set(receipt['archives']) != set(pins)-{'schema_version'}:
        raise ValueError('Unreviewed upstream archive set')
    for component, pin in receipt['archives'].items():
        upstream_mode(component,profile)
        if pin['sha256'] != pins[component]['sha256']:
            raise ValueError('Pinned upstream source differs from compilation receipt')
    output=work/'component-materials';output.mkdir(exist_ok=False)
    notices=output/'notices';notices.mkdir()
    shared=output/'shared';shared.mkdir()
    started=time.monotonic();entries={n:[] for n in ARCHIVES};omitted=[];collected=[]
    with deterministic_tar(shared/ARCHIVES[1]) as changes, deterministic_tar(shared/ARCHIVES[2]) as retained:
        def add(path,name):
            relative(name)
            if path.is_symlink() or not path.is_file():
                raise ValueError('Missing or unsafe compact source input: '+name)
            digest=sha(path);size=path.stat().st_size
            destination,reason=selection(name,profile,pins)
            if destination is None:
                omitted.append(dict(path=name,sha256=digest,size=size,reason=reason))
                return
            target=ARCHIVES[1] if destination=='changes' else ARCHIVES[2]
            with path.open('rb') as stream:
                entries[target].append(add_stream(changes if destination=='changes' else retained,
                    name,stream,size,digest,path.stat().st_mode & 0o777))
        for component,pin in sorted(receipt['archives'].items()):
            archive=work/'source-archives'/(component+'.archive')
            if sha(archive)!=pin['sha256']:
                raise ValueError('Source archive changed: '+component)
            add(archive,'archives/'+component+'.archive')
            # Preserve notices even when the full permissive archive is not shipped.
            with tarfile.open(archive) as upstream:
                for member in upstream:
                    if not member.isfile() or not notice_candidate(member.name):
                        continue
                    name=str(relative(member.name));target=notices/'upstream'/component/name
                    if target.exists():
                        raise ValueError('Duplicate upstream notice path')
                    target.parent.mkdir(parents=True,exist_ok=True)
                    with upstream.extractfile(member) as src,target.open('wb') as dst:shutil.copyfileobj(src,dst)
                    collected.append(dict(component=component,archive_sha256=pin['sha256'],
                        source_path=name,notice_path=str(target.relative_to(notices)),sha256=sha(target),
                        classification='notice-candidate-not-license-conclusion'))
        for name,digest in sorted(receipt['recipe_files'].items()):
            relative(name);path=ROOT/name
            if sha(path)!=digest:
                raise ValueError('Recipe changed after build: '+name)
            add(path,'recipe/'+name)
        build=work/'component-build'
        for path in sorted(build.rglob('*')):
            local=path.relative_to(build)
            if '__pycache__' in local.parts or path.is_dir():continue
            if any(p in ('prefix','stage','candidate','upstream') for p in local.parts):continue
            if 'build' in local.parts and path.suffix.lower() not in ('.h','.hpp','.c','.cpp','.xml','.qml','.py','.sh','.cmake','.json','.txt','.ninja'):continue
            if path.is_symlink():
                if not path.resolve(strict=True).is_relative_to(build):
                    raise ValueError('Build material link escapes workspace')
                continue
            if path.is_file():add(path,'build-materials/'+str(local))
        add(work/'component-source.json','component-source.json')
        for name in ('build-packages.txt','build-repositories.conf'):add(work/name,'environment/'+name)
        write_component_map(ROOT,receipt,notices)
        shutil.copytree(ROOT/'docs/licensing/licenses',notices/'reference-texts')
        shutil.copytree(ROOT/'vendor',notices/'vendored-source',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        (notices/'README.txt').write_text(
            'COMPONENT LICENSE AND SOURCE MATERIALS\n'
            'Existing notices and per-module grants remain intact. No blanket PolyForm restriction applies.\n'
            'Fixed permissive origins, changes and build records are delivered separately from retained upstream sources.\n'
            'KWin source and necessary build inputs are retained. Mesa/Venus archives are retained conservatively.\n'
            'Source collection does not assert full-image system-package source or legal completeness.\n')
        (notices/'upstream-index.json').write_text(json.dumps(collected,indent=2)+'\n')
        for name in ('MODULE-LICENSES.json','MODULE-NOTICES.txt'):add(notices/name,'licensing/'+name)
        origins=dict(profile=profile,component_receipt_sha256=sha(work/'component-source.json'),
            upstream={c:dict(pins[c],delivery=upstream_mode(c,profile)) for c in sorted(receipt['archives'])},
            modifications='Original recipe/vendor patches, build-materials/builders, generated definitions and build records retained.',
            licensing='Per-file terms remain intact; no PolyForm overlay on upstream/GPL materials.')
        entries[ARCHIVES[1]].append(add_bytes(changes,'SOURCE-ORIGINS.json',canonical(origins)+b'\n'))
    notice_hashes={str(p.relative_to(notices)):sha(p) for p in sorted(notices.rglob('*')) if p.is_file()}
    with deterministic_tar(shared/ARCHIVES[0]) as archive:
        for name in notice_hashes:
            entries[ARCHIVES[0]].append(add_bytes(archive,'notices/'+name,(notices/name).read_bytes()))
    index=dict(schema_version=1,projection_version=PROJECTION_VERSION,profile=profile,
        collection_mode='direct-compiler-collection',component_receipt=receipt,
        source_receipt_sha256=sha(work/'component-source.json'),original_sources=None,
        upstream=origins['upstream'],
        files=[dict(name=n,sha256=sha(shared/n),size=(shared/n).stat().st_size,entries=entries[n]) for n in ARCHIVES],
        omitted_entries=omitted,corresponding_source_complete=False,
        scope='Direct compact graphics collection; no full-rootfs system-package source completeness claim')
    index['bundle_id']=hashlib.sha256(canonical(index)).hexdigest()
    index['tag']='graphics-sources-'+profile+'-'+index['bundle_id'][:20]
    validate_index(index,receipt)
    (shared/INDEX).write_text(json.dumps(index,indent=2)+'\n')
    verify_bundle(shared)
    report=dict(schema_version=2,profile=profile,collection_complete=True,
        source_receipt_sha256=sha(work/'component-source.json'),notice_files=notice_hashes,
        source_bundle=dict(index=INDEX,index_sha256=sha(shared/INDEX),
            files=[dict(name=n,sha256=sha(shared/n),size=(shared/n).stat().st_size) for n in (*ARCHIVES,INDEX)]),
        license_review='pending',distribution_allowed=False,corresponding_source_complete=False,
        collection_mode='direct-compiler-collection',elapsed_seconds=round(time.monotonic()-started,3),
        scope='Compact shared sources; no intermediate sources.tar or copied expanded upstream trees')
    (output/'materials.json').write_text(json.dumps(report,indent=2)+'\n')
    verify(work)
    return report


def verify(work):
    directory=work/'component-materials'
    report=json.loads((directory/'materials.json').read_text())
    if report.get('schema_version')!=2 or report.get('collection_complete') is not True:
        raise ValueError('Compact source collection incomplete')
    if any(p.is_symlink() for p in directory.rglob('*')):
        raise ValueError('Material symlinks are not allowed')
    if report['source_receipt_sha256']!=sha(work/'component-source.json'):
        raise ValueError('Compact material receipt mismatch')
    shared=directory/'shared';index=verify_bundle(shared)
    receipt=json.loads((work/'component-source.json').read_text())
    validate_index(index,receipt)
    descriptor=dict(index=INDEX,index_sha256=sha(shared/INDEX),
        files=[dict(name=n,sha256=sha(shared/n),size=(shared/n).stat().st_size) for n in (*ARCHIVES,INDEX)])
    if descriptor!=report['source_bundle'] or index['source_receipt_sha256']!=report['source_receipt_sha256']:
        raise ValueError('Compact source bundle changed')
    actual={str(p.relative_to(directory/'notices')):sha(p) for p in (directory/'notices').rglob('*') if p.is_file()}
    indexed={r['path'].removeprefix('notices/'):r['sha256'] for r in index['files'][0]['entries']}
    if not actual or actual!=report['notice_files'] or actual!=indexed:
        raise ValueError('Notice materials changed')
    return report
