#!/usr/bin/env python3
"""Admit owner-approved private test artifacts without authorizing public releases."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from component_materials import sha, verify, source_files, source_descriptor
from license_inputs import paths as license_paths
from payload_contract import asset_names, source_asset_names
from source_delivery import required_assets
from contract import validate

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = 'WSLd-wsx/wsx-rootfs'


def require_private(repo, metadata):
    if repo != REPOSITORY or metadata.get('full_name') != repo or metadata.get('private') is not True:
        raise ValueError('Private artifacts require the approved private wsx-rootfs repository')


def require_policy(root, mapping):
    modules = json.loads((root/'docs/licensing/modules.json').read_text())
    if (modules.get('license_grant') is not True or modules.get('private_artifacts_allowed') is not True
            or modules.get('license_selection',{}).get('effective') is not True
            or modules.get('activation',{}).get('approved_by') != 'WGY (GitHub: wgy-wsx) <wgy@wsxdesk.com>'
            or mapping.get('license_grant') is not True
            or mapping.get('private_artifacts_allowed') is not True):
        raise ValueError('Effective owner grants and private artifact approval required')
    expected = {name:sha(root/name) for name in license_paths(root)}
    if mapping.get('policy_files') != expected:
        raise ValueError('Artifact was not built with the current active license policy')


def verify_files(directory, names):
    if len(set(names)) != len(names):
        raise ValueError('Duplicate artifact names')
    for name in names:
        path = directory/name
        if Path(name).name != name or path.is_symlink() or not path.is_file():
            raise ValueError('Missing/unsafe artifact: '+name)
    if {p.name for p in directory.iterdir()} != set(names):
        raise ValueError('Unexpected private artifact files')
    sums = ''.join(f'{sha(directory/name)}  {name}\n' for name in names if name != 'SHA256SUMS')
    if (directory/'SHA256SUMS').read_text() != sums:
        raise ValueError('Private artifact checksum set differs')


def verify_component(work):
    directory = work/'packages'
    manifest = json.loads((directory/'manifest.json').read_text())
    receipt = json.loads((work/'component-source.json').read_text())
    if (manifest.get('origin') != 'source-build' or manifest.get('source_receipt') != receipt
            or receipt.get('compiled') is not True or receipt.get('runtime_assembled') is not True
            or manifest.get('profile') not in ('omarchy','cachyos-plasma')):
        raise ValueError('Incomplete or mismatched source component build')
    name = manifest['archive']
    materials = verify(work)
    material_files = source_files(materials)
    verify_files(directory,[name,*material_files,'materials.json','manifest.json','SHA256SUMS'])
    if sha(directory/name) != manifest['sha256'] or (directory/name).stat().st_size != manifest['size']:
        raise ValueError('Component binary differs from manifest')
    if (json.loads((directory/'materials.json').read_text()) != materials
            or sha(directory/'materials.json') != manifest['materials_sha256']
            or manifest['source_materials'] != source_descriptor(materials)
            or any(sha(directory/n)!=sha(work/'component-materials'/p) for n,p in material_files.items())):
        raise ValueError('Component source delivery differs from collected materials')


def verify_rootfs(work):
    directory = work/'payload'
    manifest = validate(json.loads((directory/'manifest.json').read_text()))
    if manifest.get('source_delivery_schema') not in (1, 2):
        raise ValueError('Rootfs requires paired source delivery')
    verify_files(directory, asset_names(manifest))
    source = json.loads((directory/'sources.json').read_text())
    if required_assets(directory,source) != list(source_asset_names(manifest)):
        raise ValueError('Missing rootfs source delivery')
    if (directory/'component-source.json').read_bytes() != (work/'component-source.json').read_bytes():
        raise ValueError('Rootfs component receipt differs from admitted materials')
    archive = directory/manifest['asset_name']
    if sha(archive) != manifest['sha256'] or archive.stat().st_size != manifest['compressed_size']:
        raise ValueError('Rootfs archive differs from manifest')
    if json.loads((directory/'validation.json').read_text()).get('offline') != 'passed':
        raise ValueError('Rootfs offline validation did not pass')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',required=True)
    parser.add_argument('--kind',choices=('component','rootfs'),required=True)
    parser.add_argument('--work',type=Path,required=True)
    parser.add_argument('--public-prerelease',action='store_true')
    args=parser.parse_args()
    if args.repo != REPOSITORY:
        raise ValueError('Unapproved repository')
    metadata=json.loads(subprocess.check_output(['gh','api','repos/'+args.repo]))
    if args.kind == 'component':
        from component_registry import require_private as require_private_registry, IMAGE
        require_private_registry(os.environ.get('WSX_COMPONENT_IMAGE', IMAGE))
    elif args.public_prerelease and args.kind=='rootfs':
        from publish import require_public_candidate
        from source_delivery import check_public_source_delivery
        require_public_candidate(args.repo,json.loads((args.work/'payload/manifest.json').read_text()))
        check_public_source_delivery(args.work/'payload',json.loads((args.work/'payload/sources.json').read_text()))
    else:
        require_private(args.repo,metadata)
    for script, flags in [('audit-licenses.py',['--check']),('audit-license-modules.py',[]),('check-provenance.py',[])]:
        subprocess.run([sys.executable,str(ROOT/'scripts'/script),*flags],check=True)
    verify(args.work)
    notices = args.work/'component-materials/notices'
    if args.kind == 'rootfs':
        from image_materials import verify_image_snapshot
        verify_image_snapshot(ROOT,args.work)
        notices = args.work/'image-materials/component-materials/notices'
    mapping=json.loads((notices/'MODULE-LICENSES.json').read_text())
    require_policy(ROOT,mapping)
    (verify_component if args.kind=='component' else verify_rootfs)(args.work)
    print('Candidate artifact checks passed; hardware and whole-image license acceptance remain separate')


if __name__=='__main__':
    main()
