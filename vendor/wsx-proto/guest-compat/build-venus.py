#!/usr/bin/env python3
"""Build a pinned private Venus ICD with the Zink DRM-identity compatibility fix."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

VERSION = '26.2.4'
ARCHIVE_SHA = 'bce5f7fbebb934373b86c999a064d52fb5065878dc57f287f95346648ec832e9'
HERE = Path(__file__).resolve().parent


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--archive', required=True, type=Path)
    parser.add_argument('--nv-linear-color', action='store_true',
                        help='Include the paired NV linear-color Venus protocol extension')
    parser.add_argument('--opaque-import', action='store_true',
                        help='Build opt-in native allocation-size queries for opaque imports')
    parser.add_argument('--direct-wsi', action='store_true',
                        help='Build opt-in rejection of PRIME blit on the negotiated linear path')
    parser.add_argument('--jobs', type=int, default=3)
    parser.add_argument('--linear-layout-cache', action='store_true',
                        help='Build the opt-in per-image native LINEAR layout cache')
    parser.add_argument('--opaque-wsi', action='store_true',
                        help='Build the private opaque Wayland descriptor consumer')
    args = parser.parse_args()
    if args.opaque_wsi and not (args.direct_wsi and args.opaque_import):
        parser.error('--opaque-wsi requires --direct-wsi and --opaque-import')
    if args.jobs < 1:
        parser.error('--jobs must be positive')
    if args.opaque_import and not args.nv_linear_color:
        parser.error('--opaque-import requires --nv-linear-color')
    if sha(args.archive) != ARCHIVE_SHA:
        raise RuntimeError('Mesa source archive hash mismatch')
    if args.direct_wsi and not args.nv_linear_color:
        parser.error('--direct-wsi requires --nv-linear-color')
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    with tarfile.open(args.archive) as archive:
        archive.extractall(out, filter='data')
    source = out / ('mesa-' + VERSION)
    patch = HERE / 'venus-zink-drm-identity.patch'
    changed = 'src/virtio/vulkan/vn_wsi.c'
    patches = [patch]
    changed_files = [changed]
    if args.nv_linear_color:
        patches.append(HERE / 'venus-nv-linear-color.patch')
        changed_files += ['src/virtio/vulkan/vn_physical_device.c',
                         'src/virtio/venus-protocol/vn_protocol_driver_info.h',
                         'src/virtio/venus-protocol/vn_protocol_driver_device.h']
    if args.opaque_import:
        patches.append(HERE / 'venus-opaque-import.patch')
        changed_files.append('src/virtio/vulkan/vn_device_memory.c')
    if args.direct_wsi:
        patches.append(HERE / 'venus-direct-wsi.patch')
        if 'src/virtio/vulkan/vn_physical_device.c' not in changed_files:
            changed_files.append('src/virtio/vulkan/vn_physical_device.c')
    if args.opaque_wsi:
        patches.append(HERE / 'venus-opaque-wsi.patch')
        patches.append(HERE / 'venus-opaque-query.patch')
        patches.append(HERE / 'venus-opaque-export-order.patch')
        patches.append(HERE / 'venus-opaque-bind-order.patch')
        changed_files.append('src/virtio/vulkan/vn_image.c')
        changed_files += ['src/vulkan/util/vk_internal_exts.h',
                          'src/vulkan/wsi/wsi_common_private.h',
                          'src/vulkan/wsi/wsi_common_drm.c',
                          'src/vulkan/wsi/wsi_common_wayland.c',
                          'src/vulkan/wsi/meson.build']
    if args.linear_layout_cache:
        patches.append(HERE / 'venus-linear-layout-cache.patch')
        for name in ['src/virtio/vulkan/vn_image.c', 'src/virtio/vulkan/vn_image.h']:
            if name not in changed_files:
                changed_files.append(name)
    report = dict(passed=False, version=VERSION, archive_sha256=ARCHIVE_SHA,
                  linear_layout_cache=args.linear_layout_cache,
                  patch_sha256=sha(patch), commands=[], system_icd_replaced=False,
                  nv_linear_color_protocol=args.nv_linear_color,
                  opaque_wsi=args.opaque_wsi, opaque_import=args.opaque_import, direct_wsi="linear-v1" if args.direct_wsi else False,
                  patches={p.name: sha(p) for p in patches})
    env = dict(os.environ, PATH=str(Path(sys.executable).parent) + ':' + os.environ['PATH'])
    for key in ['LD_LIBRARY_PATH', 'LD_PRELOAD', 'PYTHONPATH', 'CC', 'CXX',
                'CFLAGS', 'CXXFLAGS', 'CPPFLAGS', 'LDFLAGS', 'PKG_CONFIG_PATH']:
        env.pop(key, None)
    meson = [sys.executable, '-m', 'mesonbuild.mesonmain']

    def run(name, argv):
        with (out / (name + '.log')).open('w') as log:
            code = subprocess.run(argv, env=env, stdout=log, stderr=subprocess.STDOUT).returncode
        report['commands'].append(dict(name=name, argv=argv, code=code))
        print(name, code, flush=True)
        if code:
            raise RuntimeError((out / (name + '.log')).read_text()[-4000:])

    try:
        for index, patch_file in enumerate(patches):
            run('patch-' + str(index), ['patch', '--batch', '--fuzz=0', '-p1',
                '-d', str(source), '-i', str(patch_file)])
        if args.opaque_wsi:
            adapter = HERE.parent / 'guest-opaque'
            target = source / 'src/vulkan/wsi/wsx'
            target.mkdir()
            for name in ['gbm-descriptor.c', 'gbm-descriptor.h', 'wsx-opaque-uapi.h']:
                shutil.copy2(adapter / name, target / name)
                changed_files.append(str((target / name).relative_to(source)))
            protocol = adapter / 'wayland/wsx-opaque-buffer-v1.xml'
            report['wayland_protocol_sha256'] = sha(protocol)
            for kind, name in [('client-header', 'wsx-opaque-buffer-v1-client.h'),
                               ('private-code', 'wsx-opaque-buffer-v1-protocol.c')]:
                run('wayland-' + kind, ['wayland-scanner', kind, str(protocol), str(target / name)])
                changed_files.append(str((target / name).relative_to(source)))
        patched_hashes = {name: sha(source / name) for name in changed_files}
        run('configure', meson + ['setup', str(out / 'build'), str(source),
            '--buildtype=release', '--wrap-mode=nofallback', '-Dgallium-drivers=[]',
            '-Dvulkan-drivers=virtio', '-Dplatforms=x11,wayland', '-Dglx=disabled',
            '-Degl=disabled', '-Dgbm=disabled', '-Dopengl=false', '-Dgles1=disabled',
            '-Dgles2=disabled', '-Dllvm=disabled', '-Dbuild-tests=false', '-Dtools=[]',
            '-Dvulkan-layers=[]'])
        run('compile', meson + ['compile', '-C', str(out / 'build'), '-j', str(args.jobs), 'vulkan_virtio'])
        with tarfile.open(args.archive) as archive:
            for member in archive:
                if not member.isfile():
                    continue
                relative = str(Path(member.name).relative_to(source.name))
                expected = patched_hashes.get(relative) or \
                    hashlib.sha256(archive.extractfile(member).read()).hexdigest()
                if sha(out / member.name) != expected:
                    raise RuntimeError('Source changed: ' + member.name)
        prefix = out / 'prefix'
        prefix.mkdir()
        shutil.copy2(out / 'build/src/virtio/vulkan/libvulkan_virtio.so', prefix)
        (prefix / 'virtio_icd.json').write_text(json.dumps({
            'file_format_version': '1.0.0',
            'ICD': {'library_path': './libvulkan_virtio.so', 'api_version': '1.4.354'}}, indent=2) + '\n')
        files = {p.name: sha(p) for p in sorted(prefix.iterdir())}
        (prefix / 'manifest.json').write_text(json.dumps(dict(version=VERSION,
            linear_layout_cache=args.linear_layout_cache,
            source_sha256=ARCHIVE_SHA, zink_drm_identity=True,
            nv_linear_color_protocol=args.nv_linear_color,
            opaque_wsi=args.opaque_wsi, opaque_import=args.opaque_import, direct_wsi="linear-v1" if args.direct_wsi else False, files=files), indent=2) + '\n')
        report.update(passed=True, patched_source_sha256=patched_hashes[changed],
                      patched_sources=patched_hashes,
                      artifacts={str(p.relative_to(out)): sha(p) for p in prefix.iterdir()})
    finally:
        (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
