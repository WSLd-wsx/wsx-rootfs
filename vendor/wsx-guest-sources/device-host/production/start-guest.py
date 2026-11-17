# SPDX-License-Identifier: MIT
"""Bind the service-published PCI instance and start its owned Omarchy unit."""
import atexit
import hashlib
import json
import os
from pathlib import Path
import pwd
import subprocess
import sys
import tempfile
import time
import uuid


def run(argv):
    print('WSX_GUEST_EXEC', repr(argv), flush=True)
    return subprocess.run(argv, check=True)


def find_device(instance):
    matches = []
    for candidate in Path('/sys/bus/pci/devices').iterdir():
        for parent in candidate.resolve(strict=True).parents:
            subsystem = parent / 'subsystem'
            if subsystem.is_symlink() and subsystem.resolve(strict=True).name == 'vmbus':
                if uuid.UUID((parent / 'device_id').read_text().strip().strip('{}')) == instance:
                    matches.append(candidate)
                break
    if len(matches) > 1:
        raise RuntimeError('Multiple PCI functions match the service instance')
    return matches[0] if matches else None


def mesa_environment(root=None, render_node=None):
    """Select the verified deployment-local graphics stack; keep system packages intact."""
    root = Path(__file__).resolve().parent if root is None else Path(root).resolve()
    prefix = root / 'mesa'
    if not prefix.exists():
        return {}
    manifest = json.loads((prefix / 'manifest.json').read_text())
    if manifest['version'] != '26.1.8':
        raise RuntimeError('Unexpected private Mesa compatibility version')
    required = {'lib/libgbm.so.1', 'lib/libEGL_mesa.so.0', 'lib/libGLX_mesa.so.0',
                'lib/libgallium-26.1.8.so', 'share/glvnd/egl_vendor.d/50_mesa.json'}
    if not required.issubset(manifest['files']):
        raise RuntimeError('Private Mesa manifest is incomplete')
    for relative, expected in manifest['files'].items():
        path = (prefix / relative).resolve(strict=True)
        if not path.is_relative_to(prefix):
            raise RuntimeError('Private Mesa file escapes its deployment')
        with path.open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != expected:
                raise RuntimeError('Private Mesa hash mismatch: ' + relative)
    print('WSX_GUEST_MESA', manifest['version'], str(prefix), flush=True)
    env = {'LD_LIBRARY_PATH': str(prefix / 'lib'),
            'LIBGL_DRIVERS_PATH': str(prefix / 'lib/dri'),
            'GBM_BACKENDS_PATH': str(prefix / 'lib/gbm'),
            'GBM_BACKEND': 'dri',
            '__GLX_VENDOR_LIBRARY_NAME': 'mesa',
            '__EGL_VENDOR_LIBRARY_FILENAMES': str(prefix / 'share/glvnd/egl_vendor.d/50_mesa.json')}
    if manifest.get('cached_host_memory_policy'):
        env['WSX_ZINK_CACHED_HOST_MEMORY'] = 'true'
    if manifest.get('presentation_staging_policy'):
        env['WSX_ZINK_PRESENTATION_FALLBACK'] = 'true'
    if manifest.get('linear_shared_compat'):
        if manifest.get('presentation_staging_policy'):
            raise RuntimeError('Direct shared linear mode cannot enable presentation staging')
        env['WSX_ZINK_LINEAR_FEEDBACK_COMPAT'] = 'true'
        env['WSX_ZINK_NEGOTIATE_EXPORT'] = 'true'
        env['WSX_ZINK_PRESENTATION_FALLBACK'] = 'false'
    icd = root / 'venus'
    if icd.exists():
        metadata = json.loads((icd / 'manifest.json').read_text())
        if metadata.get('version') != '26.2.4' or not metadata.get('zink_drm_identity'):
            raise RuntimeError('Unexpected private Venus compatibility manifest')
        if set(metadata['files']) != {'libvulkan_virtio.so', 'virtio_icd.json'}:
            raise RuntimeError('Private Venus manifest is incomplete')
        for relative, expected in metadata['files'].items():
            path = (icd / relative).resolve(strict=True)
            if not path.is_relative_to(icd):
                raise RuntimeError('Private Venus file escapes its deployment')
            with path.open('rb') as stream:
                if hashlib.file_digest(stream, 'sha256').hexdigest() != expected:
                    raise RuntimeError('Private Venus hash mismatch: ' + relative)
        env['VK_DRIVER_FILES'] = str(icd / 'virtio_icd.json')
        if metadata.get('opaque_import'):
            if not metadata.get('nv_linear_color_protocol'):
                raise RuntimeError('Opaque import requires the paired Venus capability build')
            env['WSX_VENUS_OPAQUE_IMPORT'] = '1'
    if manifest.get('linear_modifier_feedback'):
        if not manifest.get('linear_shared_compat') or not icd.exists() or metadata.get('direct_wsi') != 'linear-v1':
            raise RuntimeError('Linear modifier feedback requires paired direct WSI support')
        env['WSX_VENUS_DIRECT_WSI'] = 'linear-v1'
    consumer = root / 'opaque-consumer'
    if consumer.exists():
        # An explicit deployment opts in; existing LINEAR deployments do not
        # enter this branch. A compiler flag alone never selects a new layout.
        if not (manifest.get('opaque_consumer') and manifest.get('opaque_gbm_export') and
                icd.exists() and metadata.get('opaque_wsi') and metadata.get('opaque_import')):
            raise RuntimeError('Incomplete paired opaque consumer deployment')
        if manifest.get('presentation_staging_policy') or not render_node:
            raise RuntimeError('Opaque consumer requires direct rendering and a real DRM node')
        bundle = json.loads((consumer / 'manifest.json').read_text())
        required_consumer = {'bin/Hyprland', 'lib/libaquamarine.so.14'}
        if bundle.get('abi') != 2 or not required_consumer.issubset(bundle.get('files', {})):
            raise RuntimeError('Opaque consumer manifest is incomplete')
        for relative, expected in bundle['files'].items():
            path = (consumer / relative).resolve(strict=True)
            if not path.is_relative_to(consumer):
                raise RuntimeError('Opaque consumer file escapes its deployment')
            with path.open('rb') as stream:
                if hashlib.file_digest(stream, 'sha256').hexdigest() != expected:
                    raise RuntimeError('Opaque consumer hash mismatch: ' + relative)
        import ctypes
        class GetParam(ctypes.Structure):
            _fields_ = [('param', ctypes.c_uint64), ('value', ctypes.c_uint64)]
        libc = ctypes.CDLL(None, use_errno=True)
        fd = os.open(render_node, os.O_RDWR | os.O_CLOEXEC)
        try:
            for parameter, expected in ((0x57535801, 1), (0x57535802, 2)):
                value = ctypes.c_int()
                request = GetParam(parameter, ctypes.addressof(value))
                ctypes.set_errno(0)
                if libc.ioctl(fd, ctypes.c_ulong(0xc0106443), ctypes.byref(request)) or value.value != expected:
                    raise RuntimeError(f'Opaque kernel ABI unavailable: parameter={parameter:#x} expected={expected} actual={value.value} errno={ctypes.get_errno()}')
        finally:
            os.close(fd)
        env.update(WSX_ZINK_OPAQUE_SHARED='1', WSX_OPAQUE_COMPOSITOR='1',
                   WSX_VENUS_DIRECT_WSI='opaque-v1', WSX_ZINK_PRESENTATION_FALLBACK='false',
                   WSX_OPAQUE_COMPOSITOR_EXECUTABLE=str(consumer / 'bin/Hyprland'))
        env['LD_LIBRARY_PATH'] = str(consumer / 'lib') + ':' + env['LD_LIBRARY_PATH']
        print('WSX_OPAQUE_CONSUMER_READY abi=2 staging=0', flush=True)
    return env


def prepare_x11_directory():
    """Keep the distro X11 endpoint writable without changing WSLg's own mount."""
    target = Path('/tmp/.X11-unix')
    target.mkdir(mode=0o1777, exist_ok=True)
    if os.statvfs(target).f_flag & os.ST_RDONLY:
        source = Path('/run/wsx-x11')
        source.mkdir(mode=0o1777, exist_ok=True)
        os.chmod(source, 0o1777)
        # Preserve explicitly addressed WSLg sockets, but never select them as
        # the WSX application's display. Xwayland selects its own free number.
        for sock in Path('/mnt/wslg/.X11-unix').glob('X[0-9]*'):
            link = source / sock.name
            if not link.exists() and not link.is_symlink():
                link.symlink_to(sock)
        run(['/usr/bin/mount', '--bind', str(source), str(target)])
    if os.statvfs(target).f_flag & os.ST_RDONLY:
        raise RuntimeError('The desktop X11 socket directory is still read-only')


def desktop(card, instance):
    # Start with no inherited display and explicitly select the DRM backend.
    # PAM supplies a real login session; use its standard user runtime and bus
    # so stock UWSM, portals and activation services share the desktop session.
    account = pwd.getpwnam('omarchy')
    prepare_x11_directory()
    private_mesa = mesa_environment(render_node=card)
    deployment = Path(__file__).resolve().parent
    run(['/usr/bin/python3', '-I', str(deployment / 'session/install.py'), account.pw_dir])
    run(['/usr/bin/python3', '-I', str(deployment / 'network/install.py'),
         account.pw_dir + '/.local/share/omarchy'])
    # Hyprland appends its own long instance signature. Keep the base short
    # enough for Linux's 108-byte sockaddr_un path; mkdtemp prevents collisions.
    runtime = Path(tempfile.mkdtemp(prefix='wx-', dir='/run'))
    os.chown(runtime, account.pw_uid, account.pw_gid)
    profile = json.loads((deployment.parent / 'wsx-runtime.json').read_text())
    # WSL may expose the uinput node before its optional kernel module is
    # loaded. Load it explicitly and check the real device before spawning the
    # receiver; never mistake a stale device node for a usable backend.
    if not Path('/sys/module/uinput').exists():
        run(['/usr/bin/modprobe', 'uinput'])
    deadline = time.monotonic() + 10
    while True:
        try:
            fd = os.open('/dev/uinput', os.O_RDWR | os.O_NONBLOCK | os.O_CLOEXEC)
            os.close(fd)
            break
        except FileNotFoundError:
            if time.monotonic() >= deadline:
                raise RuntimeError('The uinput device did not appear')
            time.sleep(0.1)
    input_ready = runtime / 'input.ready'
    input_process = subprocess.Popen([str(deployment / 'wsx-input-guest'),
        str(profile['port'] + 1), str(instance), str(input_ready)],
        stdin=subprocess.DEVNULL)
    def stop_input():
        if input_process.poll() is None:
            input_process.terminate()
            try:
                input_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                input_process.kill()
                input_process.wait()
    atexit.register(stop_input)
    deadline = time.monotonic() + 20
    while not input_ready.exists():
        if input_process.poll() is not None or time.monotonic() >= deadline:
            stop_input()
            raise RuntimeError('The instance-owned input channel did not become ready')
        time.sleep(0.05)
    run(['/usr/bin/udevadm', 'settle', '--timeout=5'])
    if Path('/run/seatd.sock').exists():
        raise RuntimeError('An existing seatd socket must not be replaced')
    env = dict(PATH='/usr/bin', SEATD_VTBOUND='0')
    seat = subprocess.Popen(['/usr/bin/seatd', '-u', account.pw_name, '-l', 'info'], env=env)
    deadline = time.monotonic() + 10
    while not Path('/run/seatd.sock').exists():
        if seat.poll() is not None or time.monotonic() >= deadline:
            raise RuntimeError('The owned seatd did not become ready')
        time.sleep(0.1)
    env.update(HOME=account.pw_dir, USER=account.pw_name, LOGNAME=account.pw_name,
               PATH=account.pw_dir+'/.local/share/omarchy/bin:/usr/bin',
               XDG_RUNTIME_DIR=f'/run/user/{account.pw_uid}', OMARCHY_PATH=account.pw_dir+'/.local/share/omarchy',
               XDG_SESSION_TYPE='wayland', XDG_SESSION_CLASS='user',
               WSX_DESKTOP_INSTANCE=str(instance),
               DBUS_SESSION_BUS_ADDRESS=f'unix:path=/run/user/{account.pw_uid}/bus',
               LANG='C.UTF-8', XDG_CURRENT_DESKTOP='Hyprland',
               XDG_SESSION_DESKTOP='Hyprland', WSX_WSL_NETWORK='1', AQ_DRM_DEVICES=card, AQ_BACKEND='drm',
               LIBSEAT_BACKEND='seatd', SEATD_SOCK='/run/seatd.sock',
               MESA_LOADER_DRIVER_OVERRIDE='zink', GALLIUM_DRIVER='zink',
               VK_DRIVER_FILES='/usr/share/vulkan/icd.d/virtio_icd.json',
               # Preserve the first Venus initialization result in the unit
               # journal, before compositor teardown emits secondary errors.
               VN_DEBUG='init,result', MESA_LOG_LEVEL='debug', MESA_LOG='file',
               LIBGL_DEBUG='verbose',
               VK_LOADER_DEBUG='error,warn,info,driver')
    env.update(private_mesa)
    config = runtime / 'desktop.lua'
    config.write_text('dofile(os.getenv("HOME") .. "/.config/hypr/hyprland.lua")\n'
                      'hl.config({cursor={no_hardware_cursors=1}})\n')
    # runuser opens the installed PAM session, registering a genuine logind
    # user session for the compositor and its authentication agent. Both the
    # desktop and standard application launchers use the same runtime and bus.
    compositor = subprocess.Popen(['/usr/bin/runuser', '-u', account.pw_name, '--',
        '/usr/bin/env', *[f'{key}={value}' for key, value in env.items()],
        '/usr/bin/python3', '-I', str(deployment / 'session/enter.py'),
        private_mesa.get('WSX_OPAQUE_COMPOSITOR_EXECUTABLE', '/usr/bin/Hyprland'), '--config', str(config)], env=env, cwd=account.pw_dir)
    # The transient unit uses KillMode=control-group. Its normal exit or explicit
    # stop retires both children; no other desktop/seat process is targeted.
    try:
        result = compositor.wait()
    finally:
        stop_input()
    raise SystemExit(result)


def main():
    if os.geteuid() != 0:
        raise RuntimeError('The trusted Guest owner must run as root')
    if sys.argv[1] == '--desktop':
        return desktop(sys.argv[2], uuid.UUID(sys.argv[3]))
    instance = uuid.UUID(sys.argv[1])
    if not instance.int:
        raise ValueError('A service-origin nonzero instance is required')
    root = Path(__file__).resolve().parent
    profile = json.loads((root.parent / 'wsx-runtime.json').read_text())
    print('WSX_GUEST_START', instance, 'kernel', os.uname().release, flush=True)
    for name, file in [('drm_kms_helper', 'drm_kms_helper.ko'),
                       ('virtio_dma_buf', 'virtio_dma_buf.ko'), ('virtio_gpu', 'virtio-gpu.ko'),
                       ('virtio_msg', 'virtio_msg.ko'), ('virtio_msg_vsock', 'virtio_msg_vsock.ko')]:
        if not (Path('/sys/module') / name).exists():
            run(['/usr/bin/insmod', str(root / file)])
    deadline = time.monotonic() + 60
    while True:
        device = find_device(instance)
        if device:
            break
        if time.monotonic() >= deadline:
            raise RuntimeError('The actual service-owned PCI function did not appear')
        time.sleep(0.2)
    if int((device / 'vendor').read_text(), 16) != profile['vendor_id'] or \
       int((device / 'device').read_text(), 16) != profile['device_id']:
        raise RuntimeError('PCI identity differs from the retained native profile')
    if (device / 'driver').exists():
        raise RuntimeError('The actual PCI function already has a driver')
    print('WSX_GUEST_PCI', device.name, (device / 'resource').read_text(), flush=True)
    if Path('/sys/module/wsx_virtio_msg_pci').exists():
        driver = Path('/sys/bus/pci/drivers/wsx-virtio-msg-pci')
        bound = [p for p in driver.iterdir()
                 if p.is_symlink() and p.name != 'module']
        if bound or int(Path('/sys/module/wsx_virtio_msg_pci/refcnt').read_text()) != 0:
            raise RuntimeError('An existing Guest owner cannot be reconfigured')
        # Reconfigure only an unused module after the previous PCI device is gone.
        # Ordinary rmmod independently rejects racing references; never force it.
        run(['/usr/bin/rmmod', 'wsx_virtio_msg_pci'])
    run(['/usr/bin/insmod', str(root / 'wsx_virtio_msg_pci.ko'),
         'pci_bdf='+device.name, 'host_instance='+str(instance),
         'service_port='+str(profile['port']), 'aperture_bar=0',
         'aperture_size='+str(profile['aperture_size']),
         'device_number='+str(profile['device_number'])])
    (device / 'driver_override').write_text('wsx-virtio-msg-pci\n')
    Path('/sys/bus/pci/drivers_probe').write_text(device.name+'\n')
    if (device / 'driver').resolve(strict=True).name != 'wsx-virtio-msg-pci':
        raise RuntimeError('Actual Guest PCI owner binding failed')
    cards = []
    for card in Path('/sys/class/drm').glob('card[0-9]*'):
        if card.name[4:].isdigit() and device.resolve() in card.resolve().parents:
            cards.append('/dev/dri/'+card.name)
    if len(cards) != 1:
        raise RuntimeError(f'Expected one DRM card under the actual PCI owner, found {cards}')
    unit = 'wsx-omarchy-'+instance.hex+'.service'
    # systemd services alone do not keep a WSL distribution alive. Keep the
    # original wsl.exe invocation attached until the owned desktop unit exits.
    # --wait also propagates the unit result instead of reporting only startup.
    print('WSX_OMARCHY_UNIT_STARTING', unit, cards[0], flush=True)
    argv = ['/usr/bin/systemd-run', '--wait', '--unit='+unit, '--property=Type=exec',
         '--property=KillMode=control-group', '--property=TimeoutStopSec=30',
         '/usr/bin/python3', '-I', str(Path(__file__).resolve()),
         '--desktop', cards[0], str(instance)]
    print('WSX_GUEST_EXEC', repr(argv), flush=True)
    result = subprocess.run(argv)
    print('WSX_OMARCHY_UNIT_EXITED', unit, result.returncode, flush=True)
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
