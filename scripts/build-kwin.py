#!/usr/bin/env python3
"""Build the pinned DRM/opaque KWin consumer; never use virtual-output patches."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
from build_resources import resources

ROOT = Path(__file__).resolve().parents[1]

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def build(archive, output, prepare_only=False, jobs=None):
    jobs = resources()['jobs'] if jobs is None else jobs
    if jobs < 1:
        raise ValueError('Positive compiler concurrency required')
    pin = json.loads((ROOT/'components/sources.json').read_text())['kwin']
    provenance = json.loads((ROOT/'components/cachyos-provenance.json').read_text())
    for item in provenance['files']:
        if sha(ROOT/item['vendored_path']) != item['sha256']:
            raise ValueError('KWin adapter provenance mismatch: '+item['vendored_path'])
    if sha(archive) != pin['sha256']:
        raise ValueError('Pinned KWin archive hash mismatch')
    output.mkdir(parents=True, exist_ok=False)
    report = dict(passed=False, version=pin['version'], source_sha256=pin['sha256'],
                  hardware_validation='not_run', commands=[])
    try:
        unpack = output/'upstream'
        with tarfile.open(archive) as stream:
            stream.extractall(unpack, filter='data')
        source = unpack/('kwin-'+pin['version'])
        candidate = output/'candidate'
        candidate.mkdir()
        shutil.move(source, candidate/'source')
        (candidate/'source.json').write_text(json.dumps(dict(upstream_version=pin['version'],
            source_sha256={str(p.relative_to(candidate/'source')):sha(p)
                for p in (candidate/'source').rglob('*') if p.is_file()})))
        def run(name, command, env=None):
            with (output/(name+'.log')).open('w') as log:
                result = subprocess.run(list(map(str, command)), stdout=log, stderr=subprocess.STDOUT, env=env)
            report['commands'].append(dict(name=name, argv=list(map(str, command)), exit=result.returncode))
            if result.returncode:
                raise RuntimeError('KWin '+name+' failed; inspect '+str(output/(name+'.log')))
        run('prepare', [sys.executable, ROOT/'vendor/wsx-proto/guest-opaque/prepare-kwin.py', candidate, output/'prepared'])
        report['prepared'] = True
        if prepare_only:
            return
        packages = subprocess.check_output(['pacman','-Q'], text=True)
        (output/'packages.txt').write_text(packages)
        versions = dict(line.split(' ',1) for line in packages.splitlines())
        for name, version in {'kwin':'6.8.1-', 'plasma-workspace':'6.8.1-', 'qt6-base':'6.12.0-'}.items():
            if not versions.get(name,'').startswith(version):
                raise ValueError('Compiler/runtime ABI mismatch: '+name)
        prefix = '/opt/wsx/kwin-opaque-6.8.1'
        run('configure', ['cmake','-S',output/'prepared/source','-B',output/'build','-G','Ninja',
            '-DCMAKE_INSTALL_PREFIX='+prefix,'-DCMAKE_BUILD_TYPE=Release','-DCMAKE_SKIP_RPATH=ON',
            '-DBUILD_TESTING=OFF','-DKWIN_BUILD_KCMS=OFF','-DKWIN_BUILD_SCREENLOCKER=OFF'])
        run('compile', ['cmake','--build',output/'build','--parallel',str(jobs)])
        import os
        run('install', ['cmake','--install',output/'build'], dict(os.environ, DESTDIR=str(output/'stage')))
        shutil.copytree(output/'stage'/prefix.lstrip('/'), output/'prefix', symlinks=True)
        report['passed'] = True
    finally:
        (output/'result.json').write_text(json.dumps(report, indent=2)+'\n')

if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('archive',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--prepare-only',action='store_true')
    p.add_argument('--jobs',type=int)
    a=p.parse_args();build(a.archive.resolve(),a.output.resolve(),a.prepare_only,a.jobs)
