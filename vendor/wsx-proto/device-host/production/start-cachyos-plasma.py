# SPDX-License-Identifier: MIT
"""Bind the independent PCI instance and start its owned Plasma session."""
import atexit
import hashlib
import json
import os
from pathlib import Path
import pwd
import shlex
import signal
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


def mesa_environment(root=None):
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
        raise RuntimeError('Plasma direct sharing cannot enable staging')
    if manifest.get('linear_shared_compat'):
        env.update(WSX_ZINK_LINEAR_FEEDBACK_COMPAT='true',
                   WSX_ZINK_NEGOTIATE_EXPORT='true', WSX_ZINK_PRESENTATION_FALLBACK='false')
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
            env['WSX_VENUS_OPAQUE_IMPORT'] = '1'
    consumer = root / 'kwin-opaque'
    if consumer.exists():
        if not (manifest.get('opaque_consumer') and manifest.get('opaque_gbm_export')
                and icd.exists() and metadata.get('opaque_wsi') and metadata.get('opaque_import')):
            raise RuntimeError('Incomplete paired Plasma opaque deployment')
        bundle = json.loads((consumer / 'manifest.json').read_text())
        if bundle.get('abi') != 2 or not {'bin/kwin_wayland', 'lib/libkwin.so.6'}.issubset(bundle.get('files', {})):
            raise RuntimeError('Incomplete private KWin manifest')
        for relative, expected in bundle['files'].items():
            path = (consumer / relative).resolve(strict=True)
            if not path.is_relative_to(consumer):
                raise RuntimeError('Private KWin file escapes deployment')
            with path.open('rb') as stream:
                if hashlib.file_digest(stream, 'sha256').hexdigest() != expected:
                    raise RuntimeError('Private KWin hash mismatch: ' + relative)
        env.update(WSX_ZINK_OPAQUE_SHARED='1', WSX_OPAQUE_COMPOSITOR='1',
                   WSX_VENUS_DIRECT_WSI='opaque-v1', WSX_ZINK_PRESENTATION_FALLBACK='false',
                   PATH=str(consumer / 'bin') + ':/usr/bin')
        env['LD_LIBRARY_PATH'] = str(consumer / 'lib') + ':' + env['LD_LIBRARY_PATH']
        print('WSX_KWIN_OPAQUE_CANDIDATE abi=2 staging=0', flush=True)
    return env


def configure_plasma_service(account, env):
    """Publish the selected stack before systemd can start the compositor."""
    run(['/usr/bin/systemctl', 'start', f'user@{account.pw_uid}.service'])
    command = ['/usr/bin/systemctl', '--user', f'--machine={account.pw_name}@.host']
    state = subprocess.run(command + ['show', 'plasma-kwin_wayland.service',
                           '--property=ActiveState', '--value'],
                           check=True, text=True, capture_output=True).stdout.strip()
    if state not in ('inactive', 'failed'):
        raise RuntimeError('An existing compositor must retire before configuration changes')
    directory = Path(f'/run/user/{account.pw_uid}/systemd/user/plasma-kwin_wayland.service.d')
    directory.mkdir(parents=True, exist_ok=True)
    # Unit values use systemd quoting and percent specifier expansion.
    def quote(value):
        return '"' + value.replace('\\', '\\\\').replace('"', '\\"').replace('%', '%%') + '"'
    settings = dict(env, XDG_SESSION_ID='wsx-direct-no-logind')
    content = '[Service]\n' + ''.join(
        'Environment=' + quote(key + '=' + value) + '\n'
        for key, value in sorted(settings.items()))
    path = directory / 'wsx-opaque-candidate.conf'
    temporary = directory / '.wsx-session.tmp'
    temporary.write_text(content)
    os.chown(temporary, account.pw_uid, account.pw_gid)
    temporary.replace(path)
    run(command + ['daemon-reload'])
    print('WSX_PLASMA_ENV_READY', env['WSX_DESKTOP_INSTANCE'], flush=True)


def request_plasma_logout(account, instance):
    command = ['/usr/bin/systemctl', '--user', f'--machine={account.pw_name}@.host']
    configured = subprocess.run(command + ['show', 'plasma-kwin_wayland.service',
                                '--property=Environment', '--value'],
                                check=True, text=True, capture_output=True).stdout
    if f'WSX_DESKTOP_INSTANCE={instance}' not in shlex.split(configured):
        raise RuntimeError('Refusing to stop a different desktop instance')
    run(['/usr/bin/runuser', '-u', account.pw_name, '--', '/usr/bin/env',
         f'XDG_RUNTIME_DIR=/run/user/{account.pw_uid}',
         f'DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/{account.pw_uid}/bus',
         '/usr/bin/busctl', '--user', 'call', 'org.kde.Shutdown', '/Shutdown',
         'org.kde.Shutdown', 'logout'])
    print('WSX_PLASMA_LOGOUT_REQUESTED', instance, flush=True)


def wait_plasma_stopped(account):
    deadline = time.monotonic() + 30
    command = ['/usr/bin/systemctl', '--user', f'--machine={account.pw_name}@.host']
    while True:
        result = subprocess.run(command + ['show', 'plasma-kwin_wayland.service',
                                '--property=ActiveState', '--value'],
                                text=True, capture_output=True)
        if result.returncode == 0 and result.stdout.strip() == 'failed':
            raise RuntimeError('Compositor failed during retirement; retain native owner')
        if result.returncode == 0 and result.stdout.strip() == 'inactive':
            print('WSX_PLASMA_COMPOSITOR_RETIRED', flush=True)
            return
        if time.monotonic() >= deadline:
            raise RuntimeError('Compositor retirement not acknowledged; retain native owner')
        time.sleep(0.2)


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
    account = pwd.getpwnam('wsx')
    prepare_x11_directory()
    private_mesa = mesa_environment()
    deployment = Path(__file__).resolve().parent
    env = dict(SEATD_VTBOUND='0', HOME=account.pw_dir, USER=account.pw_name, LOGNAME=account.pw_name,
               PATH='/usr/bin',
               XDG_RUNTIME_DIR=f'/run/user/{account.pw_uid}',
               XDG_SESSION_TYPE='wayland', XDG_SESSION_CLASS='user',
               WSX_DESKTOP_INSTANCE=str(instance),
               DBUS_SESSION_BUS_ADDRESS=f'unix:path=/run/user/{account.pw_uid}/bus',
               LANG='C.UTF-8', XDG_CURRENT_DESKTOP='KDE',
               XDG_SESSION_DESKTOP='KDE', KWIN_DRM_DEVICES=card, KWIN_FORCE_SW_CURSOR='1',
               LIBSEAT_BACKEND='seatd', SEATD_SOCK='/run/seatd.sock',
               MESA_LOADER_DRIVER_OVERRIDE='zink', GALLIUM_DRIVER='zink',
               VK_DRIVER_FILES='/usr/share/vulkan/icd.d/virtio_icd.json',
               # Preserve the first Venus initialization result in the unit
               # journal, before compositor teardown emits secondary errors.
               VN_DEBUG='init,result', MESA_LOG_LEVEL='debug', MESA_LOG='file',
               LIBGL_DEBUG='verbose',
               VK_LOADER_DEBUG='error,warn,info,driver')
    env.update(private_mesa)
    configure_plasma_service(account, env)
    # Keep owned input endpoints in a collision-free session directory.
    runtime = Path(tempfile.mkdtemp(prefix='wx-', dir='/run'))
    os.chown(runtime, account.pw_uid, account.pw_gid)
    profile = json.loads((deployment.parent / 'wsx-runtime.json').read_text())
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
    # KWin's WSL no-seat backend opens evdev directly. Grant this session user
    # access only to this runtime's three identified virtual input devices.
    input_names = {'WSX Venus Wheel', 'WSX Venus Pointer', 'WSX Venus Keyboard'}
    nodes = []
    for event in Path('/sys/class/input').glob('event[0-9]*'):
        try:
            name = (event / 'device/name').read_text().strip()
        except FileNotFoundError:
            continue
        if name in input_names:
            nodes.append('/dev/input/' + event.name)
            input_names.remove(name)
    if input_names:
        raise RuntimeError('The instance input devices were not all published')
    run(['/usr/bin/setfacl', '-m', f'u:{account.pw_uid}:rw', *nodes])
    if Path('/run/seatd.sock').exists():
        raise RuntimeError('An existing seatd socket must not be replaced')
    seat = subprocess.Popen(['/usr/bin/seatd', '-u', account.pw_name, '-l', 'info'],
                            env=dict(PATH='/usr/bin', SEATD_VTBOUND='0'))
    deadline = time.monotonic() + 10
    while not Path('/run/seatd.sock').exists():
        if seat.poll() is not None or time.monotonic() >= deadline:
            raise RuntimeError('The owned seatd did not become ready')
        time.sleep(0.1)
    # runuser opens the installed PAM session, registering a genuine logind
    # user session for the compositor and its authentication agent. Both the
    # desktop and standard application launchers use the same runtime and bus.
    compositor = subprocess.Popen(['/usr/bin/runuser', '-u', account.pw_name, '--',
        '/usr/bin/env', *[f'{key}={value}' for key, value in env.items()],
        '/usr/bin/python3', '-I', str(deployment / 'session/enter.py'),
        '/usr/bin/startplasma-wayland'], env=env, cwd=account.pw_dir)
    # Mixed kill mode delivers SIGTERM to this owner first, allowing Plasma to
    # retire before the owned input and seat processes. No unrelated seat is targeted.
    stopping = False
    def stop_requested(signum, frame):
        nonlocal stopping
        stopping = True
    signal.signal(signal.SIGTERM, stop_requested)
    signal.signal(signal.SIGINT, stop_requested)
    while compositor.poll() is None:
        if stopping:
            request_plasma_logout(account, instance)
            stopping = False
        time.sleep(0.1)
    result = compositor.returncode
    # The PAM launcher can exit before the user compositor. Keep input/seat
    # ownership alive until its service acknowledges retirement.
    wait_plasma_stopped(account)
    stop_input()
    if seat.poll() is None:
        seat.terminate()
        seat.wait(timeout=5)
    raise SystemExit(result)


def main():
    if os.geteuid() != 0:
        raise RuntimeError('The trusted Guest owner must run as root')
    if sys.argv[1] == '--stop':
        account = pwd.getpwnam('wsx')
        request_plasma_logout(account, uuid.UUID(sys.argv[2]))
        return wait_plasma_stopped(account)
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
         '--property=KillMode=mixed', '--property=TimeoutStopSec=45',
         '/usr/bin/python3', '-I', str(Path(__file__).resolve()),
         '--desktop', cards[0], str(instance)]
    print('WSX_GUEST_EXEC', repr(argv), flush=True)
    result = subprocess.run(argv)
    print('WSX_OMARCHY_UNIT_EXITED', unit, result.returncode, flush=True)
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
