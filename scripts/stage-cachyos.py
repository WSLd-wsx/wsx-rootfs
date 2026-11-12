#!/usr/bin/env python3
"""Stage the audited Plasma session with instance parameters supplied by core."""
# Generator logic: GPL-2.0-or-later; source-expression exceptions below.
# Expression exceptions (also apply to these portions in source form):
# session_source() output additions/replacement strings: MIT.
# guest_source() output additions/replacement strings and the initialize-user.sh
# shell template in main(): PolyForm-Noncommercial-1.0.0.
# The remaining generator logic is GPL-2.0-or-later; copied notices are retained.
# See docs/licensing/OUTPUT-LICENSES.md for grants and full texts.
import argparse
import ast
import json
from pathlib import Path
import shutil
import runpy
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('Unexpected prototype structure: ' + old)
    return text.replace(old, new)


def session_source():
    source = (ROOT/'vendor/wsx-proto/device-host/production/start-cachyos-plasma.py').read_text()
    lines = source.splitlines(keepends=True)
    tree = ast.parse(source)
    selected = {'run', 'mesa_environment', 'configure_plasma_service', 'request_plasma_logout',
                'wait_plasma_stopped', 'prepare_x11_directory', 'desktop'}
    parts = [''.join(lines[n.lineno-1:n.end_lineno]) for n in tree.body
             if isinstance(n, ast.FunctionDef) and n.name in selected]
    if len(parts) != len(selected):
        raise ValueError('Missing audited session functions')
    # Preserve original leading notices that AST extraction otherwise omits.
    header = ''.join(lines[:tree.body[0].lineno-1])
    text = (header + '# Adapted by the WSX rootfs staging recipe from vendor/wsx-proto/device-host/production/start-cachyos-plasma.py.\n'
            'import atexit, hashlib, json, os, pwd, runpy, shlex, signal, subprocess, sys, tempfile, time, uuid\n'
            'from pathlib import Path\n\n' + '\n\n'.join(parts))
    text = runpy.run_path(str(ROOT/'scripts/graphics_debug.py'))['configure'](text)
    text = replace_once(text, "account = pwd.getpwnam('wsx')", "account = pwd.getpwnam(os.environ['WSX_USER'])")
    text = replace_once(text, "LANG='C.UTF-8', XDG_CURRENT_DESKTOP='KDE'", "LANG=os.environ['WSX_LOCALE'], XDG_CURRENT_DESKTOP='KDE'")
    text = replace_once(text, "profile = json.loads((deployment.parent / 'wsx-runtime.json').read_text())",
                        "profile = json.loads((Path('/run/wsx') / (instance.hex + '.json')).read_text())\n    if profile.get('pulse_server'):\n        env['PULSE_SERVER'] = profile['pulse_server']")
    text = replace_once(text, "str(profile['port'] + 1)", "str(profile['input_port'])")
    start = text.index('    # KWin\'s WSL no-seat backend opens evdev directly.')
    end = text.index("    run(['/usr/bin/setfacl', '-m', f'u:{account.pw_uid}:rw', *nodes])", start)
    text = text[:start] + """    try:
        nodes = runpy.run_path('/usr/lib/wsx/device-view.py')['prepare_input'](instance)
    except Exception:
        # No compositor or seat has started. Retire only this Popen child;
        # a timeout retains the ownership record and never escalates to kill.
        if input_process.poll() is None:
            input_process.terminate()
            input_process.wait(timeout=5)
        retire_owner_record(owner_path, owner_fd)
        raise
""" + text[end:]
    text = replace_once(text, 'def mesa_environment(root=None):', 'def mesa_environment(root=None, render_node=None):')
    text = replace_once(text, 'private_mesa = mesa_environment()', 'private_mesa = mesa_environment(render_node=card)')
    text = replace_once(text, "    return env\n", "    env['VN_PERF'] = 'no_async_mem_alloc' if os.environ['WSX_SHARING_PATH'] == 'linear-v1' else ''\n    return env\n")
    text = replace_once(text, "    icd = root / 'venus'\n", "    if os.environ.get('WSX_SHARING_PATH') not in ('linear-v1', 'opaque-v1'):\n        raise RuntimeError('Missing negotiated sharing path')\n    icd = root / 'venus'\n")
    text = replace_once(text, "if metadata.get('opaque_import'):", "if os.environ['WSX_SHARING_PATH'] == 'opaque-v1' and metadata.get('opaque_import'):")
    text = replace_once(text, "        env['VK_DRIVER_FILES'] = str(icd / 'virtio_icd.json')", "        env['VK_DRIVER_FILES'] = str(icd / 'virtio_icd.json')\n        if os.environ['WSX_SHARING_PATH'] == 'linear-v1':\n            if metadata.get('direct_wsi') != 'linear-v1':\n                raise RuntimeError('Missing paired LINEAR WSI support')\n            env['WSX_VENUS_DIRECT_WSI'] = 'linear-v1'")
    old = """        env.update(WSX_ZINK_OPAQUE_SHARED='1', WSX_OPAQUE_COMPOSITOR='1',
                   WSX_VENUS_DIRECT_WSI='opaque-v1', WSX_ZINK_PRESENTATION_FALLBACK='false',
                   PATH=str(consumer / 'bin') + ':/usr/bin')"""
    new = """        env['PATH'] = str(consumer / 'bin') + ':/usr/bin'
        if os.environ['WSX_SHARING_PATH'] == 'opaque-v1':
            if not render_node:
                raise RuntimeError('Opaque mode requires an identity-checked DRM node')
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
                        raise RuntimeError('Opaque kernel ABI unavailable')
            finally:
                os.close(fd)
            env.update(WSX_ZINK_OPAQUE_SHARED='1', WSX_OPAQUE_COMPOSITOR='1',
                       WSX_VENUS_DIRECT_WSI='opaque-v1', WSX_ZINK_PRESENTATION_FALLBACK='false')"""
    text = replace_once(text, old, new)
    text = replace_once(text, "    configure_plasma_service(account, env)\n", "    profile = json.loads((Path('/run/wsx') / (instance.hex + '.json')).read_text())\n    if profile.get('pulse_server'):\n        env['PULSE_SERVER'] = profile['pulse_server']\n    configure_plasma_service(account, env)\n")
    text = replace_once(text, "    profile = json.loads((Path('/run/wsx') / (instance.hex + '.json')).read_text())\n    if profile.get('pulse_server'):\n        env['PULSE_SERVER'] = profile['pulse_server']\n    input_ready", "    input_ready")
    # Keep the prototype's exact compositor guard, but permit the live process
    # itself to prove identity if a transient user-manager drop-in disappeared.
    text = replace_once(text, "    if f'WSX_DESKTOP_INSTANCE={instance}' not in shlex.split(configured):\n        raise RuntimeError('Refusing to stop a different desktop instance')", """    if f'WSX_DESKTOP_INSTANCE={instance}' not in shlex.split(configured):
        pid_text = subprocess.run(command + ['show', 'plasma-kwin_wayland.service',
                                  '--property=MainPID', '--value'], check=True,
                                  text=True, capture_output=True).stdout.strip()
        if not pid_text.isdecimal() or int(pid_text) <= 1:
            raise RuntimeError('Refusing to stop a different desktop instance')
        process = Path('/proc') / pid_text
        expected = Path('/usr/lib/wsx/runtime/kwin-opaque/bin/kwin_wayland')
        try:
            same_executable = os.path.samefile(process / 'exe', expected)
            environment = (process / 'environ').read_bytes().split(b'\\0')
        except OSError as error:
            raise RuntimeError('Cannot prove compositor identity') from error
        marker = ('WSX_DESKTOP_INSTANCE=' + str(instance)).encode()
        if not same_executable or marker not in environment:
            raise RuntimeError('Refusing to stop a different desktop instance')""")
    # Do not terminate input on an exception while a compositor may still own it.
    text = replace_once(text, '    atexit.register(stop_input)\n', '')
    text = replace_once(text, '    # Mixed kill mode delivers SIGTERM to this owner first, allowing Plasma to\n',
                        '    # Process-only kill mode signals this owner first, allowing Plasma to\n')
    owner_helpers = """def process_start_time(pid):
    # The parenthesized command may contain spaces; field 22 is after it.
    return Path('/proc', str(pid), 'stat').read_text().rsplit(')', 1)[1].split()[19]


def create_owner_record(instance, account, directory=Path('/run/wsx')):
    path = directory / (instance.hex + '.owner.json')
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    record = {'instance_id': str(instance), 'uid': account.pw_uid,
              'owner': {'pid': os.getpid(), 'start_time': process_start_time(os.getpid())},
              'children': {}}
    write_owner_record(fd, record)
    return path, fd, record


def write_owner_record(fd, record):
    payload = (json.dumps(record, sort_keys=True) + '\\n').encode()
    os.lseek(fd, 0, os.SEEK_SET)
    os.ftruncate(fd, 0)
    while payload:
        payload = payload[os.write(fd, payload):]
    os.fsync(fd)


def record_child(fd, record, name, process):
    record['children'][name] = {'pid': process.pid, 'start_time': process_start_time(process.pid)}
    write_owner_record(fd, record)


def retire_owner_record(path, fd):
    if path.is_symlink() or os.fstat(fd).st_ino != path.stat().st_ino:
        raise RuntimeError('Owner record changed; retain failure evidence')
    path.unlink()
    os.close(fd)


"""
    text = replace_once(text, 'def desktop(card, instance):', owner_helpers + 'def desktop(card, instance):')
    text = replace_once(text, "    account = pwd.getpwnam(os.environ['WSX_USER'])\n",
                        "    account = pwd.getpwnam(os.environ['WSX_USER'])\n    owner_path, owner_fd, owner = create_owner_record(instance, account)\n")
    text = replace_once(text, '        stdin=subprocess.DEVNULL)\n    def stop_input():',
                        "        stdin=subprocess.DEVNULL)\n    record_child(owner_fd, owner, 'input', input_process)\n    def stop_input():")
    text = replace_once(text, "                            env=dict(PATH='/usr/bin', SEATD_VTBOUND='0'))\n    deadline",
                        "                            env=dict(PATH='/usr/bin', SEATD_VTBOUND='0'))\n    record_child(owner_fd, owner, 'seat', seat)\n    deadline")
    text = replace_once(text, "        '/usr/bin/startplasma-wayland'], env=env, cwd=account.pw_dir)\n",
                        "        '/usr/bin/startplasma-wayland'], env=env, cwd=account.pw_dir)\n    record_child(owner_fd, owner, 'launcher', compositor)\n")
    text = replace_once(text, '    if seat.poll() is None:\n        seat.terminate()\n        seat.wait(timeout=5)\n',
                        "    if seat.poll() is not None:\n        raise RuntimeError('Seat exited before ordered retirement; retain ownership record')\n    seat.terminate()\n    seat.wait(timeout=5)\n    if Path('/run/seatd.sock').exists() or Path('/run/seatd.sock').is_symlink():\n        raise RuntimeError('Seat socket remained after retirement; retain ownership record')\n")
    text = replace_once(text, '    raise SystemExit(result)\n',
                        '    if result == 0:\n        retire_owner_record(owner_path, owner_fd)\n    raise SystemExit(result)\n')
    text += '\nif __name__ == "__main__":\n    desktop(sys.argv[1], uuid.UUID(sys.argv[2]))\n'
    ast.parse(text)
    return text


def guest_source():
    text = (ROOT/'guest/wsx-guest.py').read_text()
    text = replace_once(text, "'opaque-consumer/manifest.json'", "'kwin-opaque/manifest.json'")
    text = replace_once(text, "unit='wsx-omarchy-'", "unit='wsx-cachyos-plasma-'")
    text = replace_once(text, "'--property=KillMode=control-group'", "'--property=KillMode=process'")
    text = replace_once(text, "'--property=TimeoutStopSec=30'", "'--property=TimeoutStopSec=45'")
    text = replace_once(text, "    if args.command=='start':\n", """    if args.command=='start':
        # Never reset a failed owner or replace a retained seat without diagnosis.
        state = subprocess.run(['systemctl', 'show', unit, '--property=ActiveState',
                                '--value'], check=True, text=True, capture_output=True)
        if state.stdout.strip() != 'inactive':
            raise ValueError('Previous session has not safely retired; inspect diagnostics')
        if Path('/run/seatd.sock').exists() or Path('/run/seatd.sock').is_symlink():
            raise ValueError('Retained seat socket requires ownership diagnosis')
        owner = Path('/run/wsx') / (args.instance.hex + '.owner.json')
        if owner.exists() or owner.is_symlink():
            raise ValueError('Retained session ownership record requires diagnosis')
        linger = subprocess.run(['/usr/bin/loginctl', 'show-user', spec['user'],
                                 '--property=Linger', '--value'], check=True,
                                text=True, capture_output=True).stdout.strip()
        if linger != 'yes':
            raise ValueError('Initialized user manager lifetime is not enabled')
""")
    helper = """def check_plasma_compatibility(cpuinfo, versions, expected):
    required = {'cx16', 'lahf_lm', 'pni', 'popcnt', 'sse4_1', 'sse4_2', 'ssse3',
                'avx', 'avx2', 'bmi1', 'bmi2', 'f16c', 'fma', 'abm', 'movbe', 'xsave'}
    flagsets = [set(line.split(':', 1)[1].split()) for line in cpuinfo.splitlines()
                if line.startswith('flags') and ':' in line]
    if not flagsets or any(not required.issubset(flags) for flags in flagsets):
        raise ValueError('Private KWin requires x86-64-v3 CPU features on all Guest CPUs')
    if set(expected) != {'kwin', 'plasma-workspace', 'qt6-base'}:
        raise ValueError('Incomplete Plasma package compatibility lock')
    for name, version in expected.items():
        if versions.get(name) != version:
            raise ValueError('Private KWin dependency version mismatch: '+name)


"""
    text = replace_once(text, 'def prepare(args):', helper + 'def prepare(args):')
    text = replace_once(text, '    initialized = json.loads(STATE.read_text())',
        "    result = subprocess.run(['/usr/bin/pacman', '-Q', 'kwin', 'plasma-workspace', 'qt6-base'], check=True, text=True, capture_output=True)\n"
        "    versions = dict(line.split(' ', 1) for line in result.stdout.splitlines())\n"
        "    expected = json.loads(Path('/usr/lib/wsx/plasma-compat.json').read_text())['packages']\n"
        "    check_plasma_compatibility(Path('/proc/cpuinfo').read_text(), versions, expected)\n"
        "    initialized = json.loads(STATE.read_text())")
    text = replace_once(text, "    account = pwd.getpwnam(args.user)\n", "    run(['/usr/bin/pacman-key', '--init'])\n    run(['/usr/bin/pacman-key', '--populate', 'archlinux', 'cachyos'])\n    run(['/usr/bin/loginctl', 'enable-linger', args.user])\n    account = pwd.getpwnam(args.user)\n")
    start = text.index("    env = dict(PATH='/usr/share/omarchy/bin:/usr/bin'")
    end = text.index('    # Seed only per-user', start)
    text = text[:start] + "    env = dict(PATH='/usr/bin', HOME=account.pw_dir, USER=args.user, LOGNAME=args.user, LANG=args.locale)\n" + text[end:]
    ast.parse(text)
    return text


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('rootfs', type=Path)
    p.add_argument('components', type=Path)
    args = p.parse_args()
    root = args.rootfs.resolve(strict=True)
    runtime = root/'usr/lib/wsx/runtime'
    runtime.mkdir(parents=True)
    packages = dict(line.split(' ', 1) for line in (args.components.parent/'rootfs-packages.txt').read_text().splitlines())
    expected_prefixes = {'kwin': '6.8.1-', 'plasma-workspace': '6.8.1-', 'qt6-base': '6.12.0-'}
    for name, prefix in expected_prefixes.items():
        if not packages.get(name, '').startswith(prefix):
            raise ValueError('Private KWin dependency version mismatch: '+name+' '+packages.get(name, '<missing>'))
    lock = {'cpu_architecture_level': 'x86-64-v3', 'packages': {name: packages[name] for name in expected_prefixes}}
    (root/'usr/lib/wsx/plasma-compat.json').write_text(json.dumps(lock, indent=2)+'\n')
    for name in ('mesa', 'venus', 'kwin-opaque'):
        shutil.copytree(args.components/name, runtime/name, symlinks=True)
    helper = root/'usr/lib/plasma-setup-xwayland'
    if not helper.is_file() or not helper.stat().st_mode & 0o111:
        raise ValueError('Missing executable version-locked Plasma Xwayland helper')
    helper_link = root/'opt/wsx/kwin-opaque-6.8.1/lib/libexec/plasma-setup-xwayland'
    helper_link.parent.mkdir(parents=True, exist_ok=True)
    helper_link.symlink_to('/usr/lib/plasma-setup-xwayland')
    shutil.copytree(ROOT/'vendor/wsx-proto/session', runtime/'session')
    runpy.run_path(str(ROOT/'scripts/session_venus_policy.py'))['configure'](runtime/'session')
    (runtime/'desktop.py').write_text(session_source())
    subprocess.run(['cc', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
                    '-I'+str(ROOT/'vendor/rvgpu/include'), str(ROOT/'guest/input.c'),
                    '-o', str(runtime/'wsx-input-guest')], check=True)
    guest = root/'usr/bin/wsx-guest'
    guest.write_text(guest_source()); guest.chmod(0o755)
    init = root/'usr/lib/wsx/initialize-user.sh'
    init.write_text('#!/bin/bash\nset -euo pipefail\nxdg-user-dirs-update\n')
    init.chmod(0o755)

    runpy.run_path(str(ROOT/'scripts/stage-protocol.py'))['stage'](root, 'plasma')


if __name__ == '__main__':
    main()
