#!/usr/bin/env python3
"""Admit a pinned source component package into an empty staging directory."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import shutil
from component_materials import source_files, source_descriptor, verify

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def consume(bundle, output, profile, expected):
    manifest = json.loads((bundle/'manifest.json').read_text())
    if (manifest.get('schema_version') not in (1, 2) or manifest.get('profile') != profile
            or manifest.get('architecture') != 'x86_64' or manifest.get('origin') != 'source-build'):
        raise ValueError('Component identity mismatch')
    name = manifest['archive']
    if Path(name).name != name or not name.endswith('.tar.zst'):
        raise ValueError('Unsafe archive name')
    archive = bundle/name
    if sha(archive) != expected or manifest['sha256'] != expected or archive.stat().st_size != manifest['size']:
        raise ValueError('Pinned archive digest/size mismatch')
    if output.exists():
        raise ValueError('Fresh component destination required')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as temporary:
        temp = Path(temporary)
        with (temp/'payload.tar').open('wb') as stream:
            subprocess.run(['zstd','-dc',str(archive)],stdout=stream,check=True)
        stage = temp/'stage';stage.mkdir()
        with tarfile.open(temp/'payload.tar') as stream:
            seen = set()
            for member in stream.getmembers():
                path = Path(member.name)
                allowed = (bool(path.parts) and (path.parts[0] in ('private','component-source.json')
                    or (member.isdir() and path.parts == ('component-materials',))
                    or path.parts[:2] == ('component-materials','notices')
                    or path.parts == ('component-materials','materials.json')))
                if (path.is_absolute() or '..' in path.parts or member.name in seen
                        or not (member.isdir() or member.isfile())
                        or not allowed):
                    raise ValueError('Unsafe component archive member')
                seen.add(member.name)
            stream.extractall(stage,filter='data')
        receipt = json.loads((stage/'component-source.json').read_text())
        if receipt != manifest['source_receipt'] or receipt.get('profile','omarchy') != profile:
            raise ValueError('Source receipt mismatch')
        if receipt.get('compiled') is not True or receipt.get('runtime_assembled') is not True:
            raise ValueError('Incomplete source build')
        actual = {str(p.relative_to(stage/'private')):sha(p) for p in (stage/'private').rglob('*') if p.is_file()}
        if actual != receipt['runtime_files']:
            raise ValueError('Component payload hash mismatch')
        expected_dirs = {'mesa','venus','kwin-opaque'} if profile == 'cachyos-plasma' else {'mesa','venus','opaque-consumer'}
        if {p.name for p in (stage/'private').iterdir()} != expected_dirs:
            raise ValueError('Incomplete paired component profile')
        materials = json.loads((stage/'component-materials/materials.json').read_text())
        if (sha(bundle/'materials.json') != manifest['materials_sha256']
                or materials != json.loads((bundle/'materials.json').read_text())
                or materials['source_receipt_sha256'] != sha(stage/'component-source.json')
                or materials['schema_version'] != manifest['schema_version']
                or source_descriptor(materials) != manifest['source_materials']):
            raise ValueError('Source materials do not match the pinned runtime package')
        notices = stage/'component-materials/notices'
        notice_hashes = {str(p.relative_to(notices)):sha(p) for p in notices.rglob('*') if p.is_file()}
        if not notice_hashes or notice_hashes != materials['notice_files']:
            raise ValueError('Notice materials mismatch')
        for name,relative in source_files(materials).items():
            target=stage/'component-materials'/relative
            target.parent.mkdir(parents=True,exist_ok=True)
            if (bundle/name).is_symlink() or not (bundle/name).is_file():
                raise ValueError('Source materials missing or unsafe')
            shutil.copy2(bundle/name,target)
        try:
            verify(stage)
        except ValueError as error:
            raise ValueError('Source materials verification failed: '+str(error)) from error
        shutil.move(stage,output)

if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('bundle',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--profile',required=True,choices=('omarchy','cachyos-plasma'))
    p.add_argument('--sha256',required=True)
    a=p.parse_args();consume(a.bundle.resolve(),a.output.resolve(),a.profile,a.sha256)
