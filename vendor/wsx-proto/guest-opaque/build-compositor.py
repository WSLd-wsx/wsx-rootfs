#!/usr/bin/env python3
"""Build pinned opaque consumers privately; never install or restart a desktop."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile

HERE = Path(__file__).resolve().parent
PINS = {
    'aquamarine': ('f31c47a1b9d300847d8fc3108ad959448103dfc1', '975a3479b458722ec2e34e5fed9cdd46f77fa70485431f70093693532f685ff3'),
    'hyprland': ('efb50993780079460b0cbed1363e2166a2de1d9f', '5b05ce7ba5296fa46e666852bf108ab5af121bf577f8043787e2d2c252d8f109'),
}

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('component', choices=PINS)
    parser.add_argument('output', type=Path)
    parser.add_argument('--archive', required=True, type=Path)
    parser.add_argument('--build-deps-prefix', type=Path)
    parser.add_argument('--udis86-archive', type=Path)
    parser.add_argument('--cmake', default='cmake')
    parser.add_argument('--cmake-runtime-libs', type=Path,
                        help='Private CMake dependencies only; never a desktop runtime path')
    parser.add_argument('--jobs', type=int, default=2)
    args = parser.parse_args()
    revision, digest = PINS[args.component]
    if sha(args.archive) != digest or args.jobs < 1:
        raise ValueError('Invalid pinned archive or jobs')
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    report = dict(passed=False, component=args.component, revision=revision,
                  archive_sha256=digest, commands=[], inputs={}, installed=False,
                  real_desktop_verified=False)
    env = dict(os.environ)
    for name in ('LD_LIBRARY_PATH', 'LD_PRELOAD', 'CFLAGS', 'CXXFLAGS', 'LDFLAGS'):
        env.pop(name, None)
    if args.build_deps_prefix:
        prefix = args.build_deps_prefix.resolve()
        env['PATH'] = str(prefix/'bin') + ':' + env['PATH']
        env['CMAKE_PREFIX_PATH'] = str(prefix)
        env['PKG_CONFIG_PATH'] = str(prefix/'share/pkgconfig') + ':' + str(prefix/'lib/pkgconfig')
    if args.cmake_runtime_libs:
        env['LD_LIBRARY_PATH'] = str(args.cmake_runtime_libs.resolve())
    def run(name, command):
        with (out/(name+'.log')).open('w') as log:
            code = subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT).returncode
        report['commands'].append(dict(name=name, command=command, exit_code=code))
        print(name, code, flush=True)
        if code:
            raise RuntimeError((out/(name+'.log')).read_text()[-5000:])
    try:
        with tarfile.open(args.archive) as archive:
            archive.extractall(out, filter='data')
        source = next(p for p in out.iterdir() if p.is_dir())
        if args.component == 'hyprland':
            digest = '2f459fafa19535ef1be417bf7614e4f92475e5787d7ba76df20287cc29d1b5a9'
            if not args.udis86_archive or sha(args.udis86_archive) != digest:
                raise ValueError('The pinned Hyprland udis86 submodule archive is required')
            with tarfile.open(args.udis86_archive) as archive:
                archive.extractall(out/'submodules', filter='data')
            submodule = out/'submodules/udis86-5336633af70f3917760a6d441ff02d93477b0c86'
            shutil.copytree(submodule, source/'subprojects/udis86', dirs_exist_ok=True)
            report['inputs']['udis86_archive'] = digest
        patch = HERE/(args.component+'-opaque-consumer.patch')
        report['inputs'][patch.name] = sha(patch)
        run('patch', ['patch', '--batch', '--fuzz=0', '-p1', '-d', str(source), '-i', str(patch)])
        target = source/'wsx'
        target.mkdir()
        for name in ['gbm-descriptor.c','gbm-descriptor.h','wsx-opaque-uapi.h']:
            shutil.copy2(HERE/name, target/name)
            report['inputs'][name] = sha(HERE/name)
        if args.component == 'hyprland':
            protocol = HERE/'wayland/wsx-opaque-buffer-v1.xml'
            report['inputs'][protocol.name] = sha(protocol)
            for kind, name in [('server-header','wsx-opaque-buffer-v1-server.h'),
                               ('private-code','wsx-opaque-buffer-v1-protocol.c')]:
                run(kind, ['wayland-scanner',kind,str(protocol),str(target/name)])
        cmake = [args.cmake]
        configure = cmake+['-S',str(source),'-B',str(out/'build'),'-G','Ninja',
                          '-DCMAKE_BUILD_TYPE=Release','-DBUILD_TESTING=OFF',
                          '-DCMAKE_INSTALL_PREFIX='+str(out/'prefix')]
        if args.component == 'hyprland':
            configure += ['-DNO_HYPRPM=ON','-DNO_SYSTEMD=ON','-DNO_XWAYLAND=OFF']
        run('configure', configure)
        run('compile', cmake+['--build',str(out/'build'),'--parallel',str(args.jobs)])
        # The private prefix is an artifact, never the system installation.
        run('stage',cmake+['--install',str(out/'build')])
        report['passed'] = True
    finally:
        (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__ == '__main__':
    main()
