#!/usr/bin/env python3
"""Read back private graphics materials and report evidence without publishing."""
import argparse
import json
from pathlib import Path
import re

import component_registry as registry
from component_materials import sha, verify
from shared_sources import ROOT, REPOSITORY, INDEX, PROFILES, RETAIN_ARCHIVE, verify_bundle
import importlib.util


def load(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/name)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def inspect(work, profile):
    materials=verify(work)
    if materials['schema_version'] != 2:
        raise ValueError('This review requires direct compact collection')
    shared=work/'component-materials/shared';index=verify_bundle(shared)
    receipt=json.loads((work/'component-source.json').read_text())
    mapping=json.loads((work/'component-materials/notices/MODULE-LICENSES.json').read_text())
    load('private-artifact-gate.py').require_policy(ROOT,mapping)
    load('reuse-components.py').check_compatibility(ROOT,work)
    runtime={r['component_path']:r['sha256'] for r in mapping['component_runtime_files']}
    if runtime != receipt['runtime_files']:
        raise ValueError('Runtime license mapping differs from compilation receipt')
    entries={r['path']:r for f in index['files'] for r in f['entries']}
    for name,digest in receipt['recipe_files'].items():
        if entries.get('recipe/'+name,{}).get('sha256') != digest:
            raise ValueError('Recipe source not delivered: '+name)
    for name in ('build-packages.txt','build-repositories.conf'):
        if 'environment/'+name not in entries:
            raise ValueError('Missing build environment: '+name)
    pins=json.loads((ROOT/'components/sources.json').read_text())
    components=[]
    for component in sorted(PROFILES[profile]):
        origin=index['upstream'][component]
        if any(origin.get(k)!=v for k,v in pins[component].items()):
            raise ValueError('Upstream origin differs from fixed source input')
        notices=[n for n in entries if n.startswith('notices/upstream/'+component+'/')]
        if not notices:
            raise ValueError('No retained upstream notices: '+component)
        if component in RETAIN_ARCHIVE:
            if entries.get('archives/'+component+'.archive',{}).get('sha256') != pins[component]['sha256']:
                raise ValueError('Required original source archive absent: '+component)
        components.append(dict(component=component,delivery=origin['delivery'],notice_count=len(notices),
                               version=origin.get('version'),commit=origin.get('commit'),url=origin.get('url')))
    if profile=='cachyos-plasma' and not any(n.startswith('build-materials/kwin/') for n in entries):
        raise ValueError('Prepared KWin source/build materials missing')
    return dict(evidence_checks='passed',profile=profile,material_schema=2,
        runtime_files=len(runtime),recipe_files=len(receipt['recipe_files']),
        notice_files=len(materials['notice_files']),delivered_entries=len(entries),
        omitted_entries=len(index['omitted_entries']),components=components,
        shared_files=[{k:f[k] for k in ('name','size','sha256')} for f in index['files']],
        index_size=(shared/INDEX).stat().st_size,index_sha256=sha(shared/INDEX),
        public_distribution_approved=False,
        remaining=['Public shared source release and matching source pin are not activated by this review.',
                   'Evidence checks do not establish full-image system-package source completeness or legal ownership.',
                   'No WSL/GPU hardware validation is performed.'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile',required=True,choices=sorted(PROFILES))
    parser.add_argument('--run-id',required=True,type=int)
    parser.add_argument('--image',required=True)
    parser.add_argument('--manifest-sha256',required=True)
    parser.add_argument('--run-repository', choices=(REPOSITORY, 'WSLd-wsx/wsx-rootfs-ops'), default=REPOSITORY)
    parser.add_argument('--source-commit', default='')
    parser.add_argument('--work',required=True,type=Path)
    args=parser.parse_args()
    if not re.fullmatch('[0-9a-f]{64}',args.manifest_sha256):
        raise ValueError('Invalid manifest hash')
    helper=load('prepare-shared-sources.py')
    run=helper.api(f'repos/{args.run_repository}/actions/runs/{args.run_id}')
    source_commit = args.source_commit if args.run_repository != REPOSITORY else run['head_sha']
    if not re.fullmatch('[0-9a-f]{40}', source_commit):
        raise ValueError('Exact component source commit required')
    pin=dict(transport='ghcr',run_id=args.run_id,source_commit=source_commit,
             image=args.image,manifest_sha256=args.manifest_sha256)
    if args.run_repository != REPOSITORY:
        pin.update(run_repository=args.run_repository,workflow_commit=run['head_sha'])
    load('reuse-components.py').validate_origin(pin,args.profile,REPOSITORY,run,{})
    registry.check_reference(pin['image'])
    registry.require_private(pin['image'].split('@', 1)[0])
    args.work.mkdir(parents=True,exist_ok=False)
    package=args.work/'package';package.mkdir()
    with registry.docker_session() as env:
        registry.fetch(pin['image'],package,pin,args.profile,env)
    if sha(package/'manifest.json')!=pin['manifest_sha256']:
        raise ValueError('Package manifest differs from selected build')
    manifest=json.loads((package/'manifest.json').read_text())
    admitted=args.work/'admitted'
    load('consume-source-components.py').consume(package,admitted,args.profile,manifest['sha256'])
    report=inspect(admitted,args.profile)
    report['pin']=pin
    report['monolithic_sources_tar_present']=(package/'sources.tar').exists()
    if report['monolithic_sources_tar_present']:
        raise ValueError('Unexpected monolithic source archive')
    (args.work/'review.json').write_text(json.dumps(report,indent=2)+'\n')
    print('COMPONENT_LICENSE_REVIEW '+json.dumps(report,separators=(',',':')))


if __name__=='__main__':
    main()
