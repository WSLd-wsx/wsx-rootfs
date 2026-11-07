#!/usr/bin/env python3
"""Build pinned Mesa 26.1.8 Zink/GBM/EGL in a private prefix.

Run in Omarchy using the existing private Meson Python environment. This does
not build an ICD, replace distribution files, start a desktop or reset a device.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import shutil
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[3]


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--cached-host-memory', action='store_true',
                        help='Add the opt-in cached host-memory allocation policy')
    parser.add_argument("--presentation-staging", action="store_true",
                        help="Build capability-selected optimal-render/linear-export GPU staging")
    parser.add_argument('--import-diagnostics', action='store_true',
                        help='Log bounded DMA-BUF import rejection details')
    parser.add_argument('--negotiated-export', action='store_true',
                        help='Build opt-in export modifier enumeration; consumer admission remains required')
    parser.add_argument('--modifier-features2', action='store_true',
                        help='Preserve 64-bit DRM modifier format features with legacy fallback')
    parser.add_argument('--linear-feedback-compat', action='store_true',
                        help='Build opt-in, capability-gated linear feedback compatibility')
    parser.add_argument('--linear-shared-compat', action='store_true',
                        help='Build negotiated shared linear usage and transactional rebind')
    parser.add_argument('--linear-modifier-feedback', action='store_true',
                        help='Expose negotiated linear renderability and track native WSI layouts')
    parser.add_argument('--linear-depth-segregation', action='store_true',
                        help='Reject conditional LINEAR/depth combinations without enabling a copy fallback')
    parser.add_argument('--opaque-gbm-export', action='store_true',
                        help='Build opt-in OPTIMAL external export with paired PRIME descriptor registration')
    parser.add_argument('--opaque-consumer', action='store_true',
                        help='Build the paired opaque descriptor import extension')
    parser.add_argument('--gbm-shared-contract', action='store_true',
                        help='Build opt-in explicit modifier allocation and shared-format admission checks')
    args = parser.parse_args()
    if args.opaque_consumer and not args.opaque_gbm_export:
        parser.error('--opaque-consumer requires --opaque-gbm-export')
    if args.opaque_gbm_export and (not args.linear_depth_segregation or args.presentation_staging):
        parser.error('--opaque-gbm-export requires --linear-depth-segregation and forbids staging')
    if args.linear_depth_segregation and not args.linear_modifier_feedback:
        parser.error('--linear-depth-segregation requires --linear-modifier-feedback')
    if args.linear_modifier_feedback and not args.linear_shared_compat:
        parser.error('--linear-modifier-feedback requires --linear-shared-compat')
    if args.linear_shared_compat and not (args.linear_feedback_compat and
            args.modifier_features2 and args.negotiated_export and args.import_diagnostics):
        parser.error('--linear-shared-compat requires --linear-feedback-compat, '
                     '--modifier-features2, --negotiated-export and --import-diagnostics')
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    pin = json.loads((ROOT / 'prototypes/venus-rutabaga/sources.lock.json').read_text())['archives']['mesa']
    assert pin['version'] == '26.1.8'
    archive = ROOT / 'artifacts/venus-rutabaga/inputs-01' / pin['file']
    assert sha(archive) == pin['sha256']
    with tarfile.open(archive) as tar:
        tar.extractall(out, filter='data')
    source = out / pin['directory']
    report = {'pass': False, 'source': pin, 'commands': [], 'source_patched': False,
              'icd_built': False, 'system_libraries_replaced': False,
              'desktop_started': False, 'gpu_started': False}
    env = dict(os.environ, PATH=str(Path(sys.executable).parent) + ':' + os.environ['PATH'])
    for key in ['LD_LIBRARY_PATH', 'LD_PRELOAD', 'PYTHONPATH', 'CC', 'CXX',
                'CFLAGS', 'CXXFLAGS', 'CPPFLAGS', 'LDFLAGS', 'PKG_CONFIG_PATH']:
        env.pop(key, None)
    meson = [sys.executable, '-m', 'mesonbuild.mesonmain']

    def run(name, command):
        with (out / (name + '.log')).open('w') as log:
            proc = subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT)
        report['commands'].append({'name': name, 'argv': command, 'exit_code': proc.returncode})
        print(name, proc.returncode, flush=True)
        if proc.returncode:
            print((out / (name + '.log')).read_text()[-5000:], flush=True)
            raise RuntimeError(name)

    changed = {}
    try:
        if args.cached_host_memory:
            patch = Path(__file__).with_name('cached-host-memory.patch')
            run('allocation-policy', ['patch', '--batch', '--fuzz=0', '-p1', '-d', str(source), '-i', str(patch)])
            relative = 'src/gallium/drivers/zink/zink_screen.c'
            changed[pin['directory'] + '/' + relative] = sha(source / relative)
            report.update(source_patched=True, allocation_policy_patch_sha256=sha(patch),
                          changed_source_files=changed)
        if args.presentation_staging:
            patch = Path(__file__).with_name('presentation-staging.patch')
            run('presentation-policy', ['patch', '--batch', '--fuzz=0', '-p1', '-d', str(source), '-i', str(patch)])
            for name in ['zink_types.h', 'zink_resource.c', 'zink_context.c']:
                relative = 'src/gallium/drivers/zink/' + name
                changed[pin['directory'] + '/' + relative] = sha(source / relative)
            report.update(source_patched=True, presentation_policy_patch_sha256=sha(patch),
                          changed_source_files=changed)
        if args.import_diagnostics:
            patch = Path(__file__).with_name('import-diagnostics.patch')
            run('import-diagnostics', ['patch', '--batch', '--fuzz=0', '-p1', '-d', str(source), '-i', str(patch)])
            for relative in ['src/gallium/frontends/dri/dri2.c',
                             'src/gallium/drivers/zink/zink_resource.c']:
                changed[pin['directory'] + '/' + relative] = sha(source / relative)
            report.update(source_patched=True, import_diagnostics_patch_sha256=sha(patch),
                          changed_source_files=changed)
        if args.negotiated_export:
            patch = Path(__file__).with_name('negotiated-export.patch')
            run('negotiated-export', ['patch', '--batch', '--fuzz=0', '-p1', '-d', str(source), '-i', str(patch)])
            relative = 'src/gallium/drivers/zink/zink_resource.c'
            changed[pin['directory'] + '/' + relative] = sha(source / relative)
            report.update(source_patched=True, negotiated_export_patch_sha256=sha(patch),
                          changed_source_files=changed)
        if args.modifier_features2:
            patch = Path(__file__).with_name('modifier-features2.patch')
            run('modifier-features2', ['patch', '--batch', '--fuzz=0', '-p1', '-d', str(source), '-i', str(patch)])
            for name in ['zink_resource.c', 'zink_screen.c', 'zink_types.h']:
                relative = 'src/gallium/drivers/zink/' + name
                changed[pin['directory'] + '/' + relative] = sha(source / relative)
            report.update(source_patched=True, modifier_features2_patch_sha256=sha(patch),
                          changed_source_files=changed)
        if args.linear_feedback_compat:
            patch = Path(__file__).with_name('linear-feedback-compat.patch')
            run('linear-feedback-compat', ['patch', '--batch', '--fuzz=0', '-p1', '-d', str(source), '-i', str(patch)])
            relative = 'src/gallium/drivers/zink/zink_screen.c'
            changed[pin['directory'] + '/' + relative] = sha(source / relative)
            report.update(source_patched=True, linear_feedback_compat_patch_sha256=sha(patch),
                          changed_source_files=changed)
        if args.linear_shared_compat:
            patch = Path(__file__).with_name('linear-shared-compat.patch')
            run('linear-shared-compat', ['patch', '--batch', '--fuzz=0', '-p1',
                '-d', str(source), '-i', str(patch)])
            for name in ['zink_resource.c', 'zink_types.h', 'zink_screen.c',
                         'zink_context.c', 'zink_clear.c']:
                relative = 'src/gallium/drivers/zink/' + name
                changed[pin['directory'] + '/' + relative] = sha(source / relative)
            report.update(source_patched=True, linear_shared_compat_patch_sha256=sha(patch),
                          changed_source_files=changed)
        if args.linear_modifier_feedback:
            patch = Path(__file__).with_name('linear-modifier-feedback.patch')
            run('linear-modifier-feedback', ['patch', '--batch', '--fuzz=0', '-p1',
                '-d', str(source), '-i', str(patch)])
            for name in ['zink_screen.c', 'zink_kopper.c', 'zink_kopper.h', 'zink_context.c', 'zink_types.h']:
                relative = 'src/gallium/drivers/zink/' + name
                changed[pin['directory'] + '/' + relative] = sha(source / relative)
            report.update(source_patched=True, linear_modifier_feedback_patch_sha256=sha(patch),
                          changed_source_files=changed)
        if args.linear_depth_segregation:
            patch = Path(__file__).with_name('linear-depth-segregation.patch')
            run('linear-depth-segregation', ['patch', '--batch', '--fuzz=0', '-p1',
                '-d', str(source), '-i', str(patch)])
            for name in ['zink_wsx_layout.h', 'zink_context.c', 'zink_types.h',
                         'zink_resource.c', 'zink_kopper.c']:
                relative = 'src/gallium/drivers/zink/' + name
                changed[pin['directory'] + '/' + relative] = sha(source / relative)
            report.update(source_patched=True, linear_depth_segregation_patch_sha256=sha(patch),
                          changed_source_files=changed)
        if args.opaque_gbm_export:
            patch = Path(__file__).with_name('opaque-gbm-export.patch')
            run('opaque-gbm-export', ['patch', '--batch', '--fuzz=0', '-p1',
                '-d', str(source), '-i', str(patch)])
            for name in ['zink_resource.c', 'zink_types.h', 'meson.build']:
                relative = 'src/gallium/drivers/zink/' + name
                changed[pin['directory'] + '/' + relative] = sha(source / relative)
            relative = 'src/gallium/frontends/dri/dri2.c'
            changed[pin['directory'] + '/' + relative] = sha(source / relative)
            adapter = Path(__file__).parent.parent / 'guest-opaque'
            target = source / 'src/gallium/drivers/zink/wsx'
            target.mkdir()
            adapter_hashes = {}
            for name in ['gbm-descriptor.c', 'gbm-descriptor.h', 'wsx-opaque-uapi.h']:
                shutil.copy2(adapter / name, target / name)
                adapter_hashes[name] = sha(adapter / name)
                changed[str((target / name).relative_to(out))] = sha(target / name)
            report.update(source_patched=True, opaque_gbm_export_patch_sha256=sha(patch),
                          opaque_gbm_adapter_inputs=adapter_hashes, changed_source_files=changed)
        if args.opaque_consumer:
            patch = Path(__file__).with_name('opaque-consumer.patch')
            run('opaque-consumer', ['patch', '--batch', '--fuzz=0', '-p1',
                '-d', str(source), '-i', str(patch)])
            for relative in ['src/gallium/drivers/zink/zink_resource.c',
                             'src/egl/main/egldisplay.h', 'src/egl/main/eglapi.c',
                             'src/egl/main/eglimage.h', 'src/egl/main/eglimage.c',
                             'src/egl/meson.build', 'src/egl/drivers/dri2/egl_dri2.c']:
                changed[pin['directory'] + '/' + relative] = sha(source / relative)
            target = source / 'src/egl/wsx'
            target.mkdir()
            for name in ['gbm-descriptor.c', 'gbm-descriptor.h', 'wsx-opaque-uapi.h']:
                shutil.copy2(adapter / name, target / name)
                changed[str((target / name).relative_to(out))] = sha(target / name)
            report.update(opaque_consumer_patch_sha256=sha(patch), changed_source_files=changed)
        if args.gbm_shared_contract:
            contract_patches = {}
            for name, relative in [
                ('gbm-modifier-contract.patch', 'src/gbm/main/gbm.c'),
                ('gbm-shared-format-contract.patch', 'src/gbm/backends/dri/gbm_dri.c'),
            ]:
                patch = Path(__file__).with_name(name)
                run(name.removesuffix('.patch'), ['patch', '--batch', '--fuzz=0', '-p1',
                    '-d', str(source), '-i', str(patch)])
                contract_patches[name] = sha(patch)
                changed[pin['directory'] + '/' + relative] = sha(source / relative)
            report.update(gbm_shared_contract_patches=contract_patches,
                          changed_source_files=changed)
        run('configure', meson + ['setup', str(out / 'build'), str(source),
            '--prefix=' + str(out / 'prefix'), '--libdir=lib', '--wrap-mode=nofallback',
            '--buildtype=release', '-Dgallium-drivers=zink', '-Dvulkan-drivers=[]',
            '-Dplatforms=x11,wayland', '-Dglx=dri', '-Dglvnd=enabled',
            '-Degl=enabled', '-Dgbm=enabled', '-Dopengl=true', '-Dgles1=disabled',
            '-Dgles2=enabled', '-Dllvm=disabled', '-Dvideo-codecs=[]',
            '-Dbuild-tests=false', '-Dtools=[]', '-Dvulkan-layers=[]'])
        run('compile', meson + ['compile', '-C', str(out / 'build'), '-j', '3'])
        run('private-stage', meson + ['install', '-C', str(out / 'build'), '--no-rebuild'])
        prefix = out / 'prefix'
        for rel in ['lib/libgbm.so.1', 'lib/libEGL_mesa.so.0', 'lib/libGLX_mesa.so.0',
                    'lib/libgallium-26.1.8.so', 'share/glvnd/egl_vendor.d/50_mesa.json']:
            if not (prefix / rel).is_file():
                raise RuntimeError('Missing private runtime file: ' + rel)
        manifest = {'version': '26.1.8', 'source_sha256': pin['sha256'],
                    'cached_host_memory_policy': args.cached_host_memory,
                    'presentation_staging_policy': args.presentation_staging,
                    'linear_shared_compat': args.linear_shared_compat,
                    'opaque_gbm_export': args.opaque_gbm_export,
                    'opaque_consumer': args.opaque_consumer,
                    'gbm_shared_contract': args.gbm_shared_contract,
                    'linear_depth_segregation': args.linear_depth_segregation,
                    'linear_modifier_feedback': args.linear_modifier_feedback,
                    'files': {str(p.relative_to(prefix)): sha(p)
                              for p in sorted(prefix.rglob('*')) if p.is_file()}}
        (prefix / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        # Check source members again after generators and compilation have run.
        with tarfile.open(archive) as tar:
            for member in tar:
                if member.isfile():
                    if member.name in changed:
                        if sha(out / member.name) != changed[member.name]:
                            raise RuntimeError('Patched source changed during build: ' + member.name)
                        continue
                    if hashlib.sha256(tar.extractfile(member).read()).hexdigest() != sha(out / member.name):
                        raise RuntimeError('Upstream source changed: ' + member.name)
        report['artifacts'] = {str(p.relative_to(out)): sha(p)
                               for p in sorted(prefix.rglob('*')) if p.is_file()}
        report['pass'] = True
    finally:
        report['builder_sha256'] = sha(Path(__file__))
        (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
