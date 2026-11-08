#!/usr/bin/env python3
"""Fetch an explicitly pinned same-repository component artifact; never rebuild."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tarfile
import tempfile
import zipfile
from component_materials import sha, verify
from license_inputs import paths as license_paths
import component_registry as registry

ROOT = Path(__file__).resolve().parents[1]
LEGACY_COLLECTOR_SHA256 = '39659240e00ab3e45c1ba29c57e98712b7256326e2f7a767510207349b793edc'


def collection_only_change(root, name, recorded):
    """One hash-bound post-assembly collector migration, never a compiler exception."""
    if name == 'docs/provenance.json':
        # The sole change records the image-only Omarchy 4.5.0 network adapter.
        return (recorded == 'b3278806dd5622b36944dadf49031d540fccdc2ad87f6643e7d06b3e7b1d1b7e'
                and sha(root/name) == 'def155a5b243d32e41be9d17e32d969b73533ad89a80c4be17f98ebf6377caa4')
    if name == 'scripts/shared_sources.py':
        # Reviewed metadata-reader changes only; no compiled component inputs change.
        return ((recorded == '91477d2198784f904c10c01b8326d4d8a8091c5252cc8802fc430dc9806aed2f'
                 and sha(root/name) == '10ac2f902653d2969f894f6ae501d90ae08fca973795721b53e767c21efbfdde')
                or (recorded == '2bd3704a025829b397b14d053c45d1ca36f2201d1afc444262306aeaf54ed7c7'
                and sha(root/name) in {'32c6b645d21b7ab10057bad9d5d4f957978c836a58897e152d19d4257b6ac07c',
                                       '2896273adafdd77298a439f2404f4c2bfe22f44b6af9a6b0eca039d2add3e449',
                                       '10ac2f902653d2969f894f6ae501d90ae08fca973795721b53e767c21efbfdde'}))
    if name != 'scripts/component_materials.py' or recorded != LEGACY_COLLECTOR_SHA256:
        return False
    config=root/'components/source-delivery.json'
    if not config.is_file():
        return False
    migration=json.loads(config.read_text()).get('postbuild_collector_migration',{})
    return (migration.get('from_sha256') == LEGACY_COLLECTOR_SHA256
            and migration.get('to_sha256') == sha(root/name))


def pin_for(root, profile):
    document = json.loads((root/'components/reuse.json').read_text())
    pin = document['profiles'][profile]
    if document.get('schema_version') != 1 or not isinstance(pin, dict):
        raise ValueError('No pinned component package for '+profile+'; build and approve a package first')
    transport = pin.get('transport', 'artifact')
    if transport not in ('artifact', 'ghcr'):
        raise ValueError('Unknown component transport')
    if transport == 'ghcr':
        registry.check_reference(pin.get('image', ''))
    for field in (('run_id',) if transport == 'ghcr' else ('run_id', 'artifact_id')):
        if type(pin.get(field)) is not int or pin[field] <= 0:
            raise ValueError('Invalid component pin: '+field)
    for field, length in (('source_commit',40), ('manifest_sha256',64)):
        if not re.fullmatch('[0-9a-f]{'+str(length)+'}', pin.get(field,'')):
            raise ValueError('Invalid component pin: '+field)
    return pin


def validate_origin(pin, profile, repo, run, artifact):
    run_repo = pin.get('run_repository', repo)
    if run_repo == repo:
        expected_head = pin['source_commit']
    elif run_repo == 'WSLd-wsx/wsx-rootfs-ops' and pin.get('transport') == 'ghcr':
        expected_head = pin.get('workflow_commit', '')
        if not re.fullmatch('[0-9a-f]{40}', expected_head):
            raise ValueError('Missing immutable operations workflow commit')
        if run.get('head_branch') != 'main':
            raise ValueError('Operations component build must use the main branch')
        registry.check_reference(pin.get('image', ''))
        if not pin['image'].startswith(registry.OPS_IMAGE + '@sha256:'):
            raise ValueError('Operations build must use the operations component package')
    else:
        raise ValueError('Unapproved component workflow repository')
    if (run.get('conclusion') != 'success' or run.get('status') != 'completed'
            or run.get('event') != 'workflow_dispatch'
            or run.get('path') != '.github/workflows/components.yml'
            or run.get('head_sha') != expected_head
            or run.get('repository',{}).get('full_name') != run_repo
            or run.get('head_repository',{}).get('full_name') != run_repo):
        raise ValueError('Component workflow origin mismatch or unsuccessful run')
    if pin.get('transport') == 'ghcr':
        registry.check_reference(pin['image'])
        return
    if (artifact.get('id') != pin['artifact_id'] or artifact.get('expired') is not False
            or artifact.get('workflow_run',{}).get('id') != pin['run_id']
            or artifact.get('workflow_run',{}).get('head_sha') != pin['source_commit']
            or artifact.get('name') != profile+'-source-components-'+pin['source_commit']):
        raise ValueError('Component artifact mismatch or expired; no automatic rebuild')


def unpack(archive, destination):
    with zipfile.ZipFile(archive) as stream:
        seen = set()
        for member in stream.infolist():
            name = member.filename
            path = Path(name)
            mode = member.external_attr >> 16
            if (path.is_absolute() or '..' in path.parts or len(path.parts) != 1
                    or name in seen or member.is_dir() or stat.S_ISLNK(mode)):
                raise ValueError('Unsafe component artifact member')
            seen.add(name)
        stream.extractall(destination)


def check_compatibility(root, work):
    from image_materials import check_component_inputs
    check_component_inputs(root, work, collection_only_change)


def restore_environment(work):
    report = verify(work)
    if report['schema_version'] == 1:
        records = {entry['path']:entry for entry in report['source_entries']}
        archive_path=work/'component-materials/sources.tar'
    else:
        from shared_sources import INDEX, ARCHIVES
        index=json.loads((work/'component-materials/shared'/INDEX).read_text())
        records={entry['path']:entry for entry in index['files'][1]['entries']}
        archive_path=work/'component-materials/shared'/ARCHIVES[1]
    destination = work/'components'; destination.mkdir(exist_ok=True)
    with tarfile.open(archive_path) as stream:
        for name in ('build-packages.txt','build-repositories.conf'):
            member_name = 'environment/'+name
            matches = [m for m in stream.getmembers() if m.name == member_name]
            if len(matches) != 1 or not matches[0].isfile():
                raise ValueError('Missing or ambiguous component build environment')
            target = destination/name
            with stream.extractfile(matches[0]) as source, target.open('wb') as output:
                shutil.copyfileobj(source, output)
            if sha(target) != records[member_name]['sha256']:
                raise ValueError('Component build environment hash mismatch')


def published_registry_origin(root, pin, profile):
    # Actions logs can expire independently of an immutable registry package.
    # Admission uses the reviewed OCI digest/labels plus the separately published,
    # digest-checked exact source receipt; a missing run is never called successful.
    import shared_sources
    config = json.loads((root/'components/source-delivery.json').read_text())
    original = config.get('component_origins', {}).get(profile)
    if not isinstance(original, dict) or not isinstance(pin, dict):
        raise ValueError('Registry pin differs from published source origin')
    registry.check_reference(original.get('image', ''))
    registry.check_reference(pin.get('image', ''))
    if ({k:v for k,v in original.items() if k != 'image'} != {k:v for k,v in pin.items() if k != 'image'}
            or original['image'].split('@', 1)[1] != pin['image'].split('@', 1)[1]):
        raise ValueError('Registry pin differs from published source origin')
    return json.loads(shared_sources.download_index(shared_sources.pin_for(root,profile),profile))


def verify_published_receipt(index, work):
    receipt = json.loads((work/'component-source.json').read_text())
    if index.get('component_receipt') != receipt or index.get('source_receipt_sha256') != sha(work/'component-source.json'):
        raise ValueError('Registry component differs from the published source receipt')


def acquire(root, work, profile, repo):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo):
        raise ValueError('Invalid repository')
    pin = pin_for(root, profile)
    def api(path):
        return json.loads(subprocess.check_output(['gh','api',f'repos/{repo}/'+path]))
    is_registry = pin.get('transport') == 'ghcr'
    if is_registry:
        if repo != registry.REPOSITORY:
            raise ValueError('Registry reuse is restricted to the approved repository')
        source_index = published_registry_origin(root,pin,profile)
    else:
        run = api(f'actions/runs/{pin["run_id"]}')
        artifact = api(f'actions/artifacts/{pin["artifact_id"]}')
        validate_origin(pin, profile, repo, run, artifact)
    work.mkdir(parents=True,exist_ok=True)
    for name in ('private','component-source.json','component-materials','component-reuse.json'):
        if (work/name).exists():
            raise ValueError('Component staging already exists: '+name)
    with tempfile.TemporaryDirectory(dir=work) as temporary:
        temp = Path(temporary); bundle = temp/'bundle'; bundle.mkdir()
        if is_registry:
            registry.require_private(pin['image'].split('@', 1)[0])
            with registry.docker_session() as env:
                registry.fetch(pin['image'], bundle, pin, profile, env)
        else:
            with (temp/'artifact.zip').open('wb') as output:
                subprocess.run(['gh','api',f'repos/{repo}/actions/artifacts/{pin["artifact_id"]}/zip'],stdout=output,check=True)
            unpack(temp/'artifact.zip', bundle)
        if sha(bundle/'manifest.json') != pin['manifest_sha256']:
            raise ValueError('Pinned component manifest changed')
        manifest = json.loads((bundle/'manifest.json').read_text())
        spec = importlib.util.spec_from_file_location('component_consumer',root/'scripts/consume-source-components.py')
        consumer = importlib.util.module_from_spec(spec); spec.loader.exec_module(consumer)
        admitted = temp/'admitted'
        consumer.consume(bundle, admitted, profile, manifest['sha256'])
        if is_registry:
            verify_published_receipt(source_index,admitted)
        check_compatibility(root, admitted)
        restore_environment(admitted)
        for path in admitted.iterdir():
            if (work/path.name).exists():
                raise ValueError('Component destination conflict: '+path.name)
        for path in admitted.iterdir():
            shutil.move(path,work/path.name)
    from image_materials import image_snapshot
    image_snapshot(root,work)
    (work/'component-reuse.json').write_text(json.dumps(dict(schema_version=1, repository=repo,
        profile=profile, pin=pin, archive_sha256=manifest['sha256'], rebuilt=False,
        origin_verification='immutable-registry-and-public-source' if is_registry else 'live-actions-artifact'),indent=2)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile',required=True,choices=('omarchy','cachyos-plasma'))
    parser.add_argument('--repo',required=True)
    parser.add_argument('--work',type=Path,required=True)
    parser.add_argument('--check-pin',action='store_true')
    args=parser.parse_args()
    if args.check_pin:
        print(json.dumps(pin_for(ROOT,args.profile)))
    else:
        acquire(ROOT,args.work,args.profile,args.repo)
