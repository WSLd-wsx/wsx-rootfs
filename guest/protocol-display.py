# Original WSX code, PolyForm-Noncommercial-1.0.0.
# Migrated from wsld/core/guest/desktop-display.py; Guest owns compositor details.
"""Instance-bound runtime display control for admitted Hyprland and KWin Guests.

No user config edits, installation, daemon or shell execution. Core supplies only
numeric mode/scale choices; the monitor and compositor identities are discovered.
"""
import json
import math
import os
from pathlib import Path
import pwd
import re
import stat
import subprocess
import sys
import time
import uuid


def trusted(path, limit=65536):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    with os.fdopen(fd) as stream:
        st = os.fstat(stream.fileno())
        if not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or st.st_mode & 0o022 or st.st_size > limit:
            raise ValueError('Untrusted Guest display descriptor')
        return json.load(stream)


def context(instance):
    instance = uuid.UUID(instance)
    spec = trusted('/run/wsx/' + instance.hex + '.json')
    if uuid.UUID(spec['instance_id']) != instance:
        raise ValueError('Guest display instance mismatch')
    user = pwd.getpwnam(spec['user'])
    if not user.pw_uid:
        raise ValueError('Non-root compositor required')
    matches = []
    for proc in Path('/proc').iterdir():
        if not proc.name.isdecimal():
            continue
        try:
            if proc.stat().st_uid != user.pw_uid or (proc/'comm').read_text().strip() != 'Hyprland':
                continue
            env = dict(item.split('=', 1) for item in (proc/'environ').read_bytes().decode().split('\0') if '=' in item)
            if env.get('WSX_DESKTOP_INSTANCE') != str(instance):
                continue
            if env.get('AQ_DRM_DEVICES') != spec['drm_node'] or (proc/'exe').resolve() != Path('/usr/lib/wsx/runtime/opaque-consumer/bin/Hyprland'):
                raise ValueError('Compositor device or executable differs from admitted Guest')
            matches.append(int(proc.name))
        except (FileNotFoundError, ProcessLookupError):
            continue
    if len(matches) != 1:
        raise ValueError('No unique compositor for the admitted Guest instance')
    runtime = '/run/user/' + str(user.pw_uid)
    base = ['/usr/bin/runuser', '-u', user.pw_name, '--', '/usr/bin/env',
            'XDG_RUNTIME_DIR=' + runtime, '/usr/bin/hyprctl']
    def call(args):
        result = subprocess.run(base + args, capture_output=True, text=True, timeout=5)
        if result.returncode or len(result.stdout) > 1024*1024:
            raise RuntimeError('Guest compositor control failed: ' + result.stderr[:1024])
        return result.stdout
    instances = json.loads(call(['-j', 'instances']))
    selected = [i for i in instances if i['pid'] == matches[0]]
    if len(selected) != 1 or not re.fullmatch(r'[A-Za-z0-9_.-]{1,200}', selected[0]['instance']):
        raise ValueError('Compositor socket identity is unresolved')
    base.extend(['-i', selected[0]['instance']])
    return call, matches[0], selected[0]['instance']


def output(call):
    monitors = json.loads(call(['-j', 'monitors', 'all']))
    enabled = [m for m in monitors if not m.get('disabled')]
    if len(enabled) != 1:
        raise ValueError('Display fitting currently requires one active Guest output')
    monitor = enabled[0]
    if not re.fullmatch(r'[A-Za-z0-9_.-]{1,128}', monitor['name']) or monitor['transform'] != 0:
        raise ValueError('Unsupported Guest output name or transform')
    return monitor


def modes(monitor):
    result = []
    for value in monitor['availableModes']:
        match = re.fullmatch(r'(\d+)x(\d+)@(\d+(?:\.\d+)?)Hz', value)
        if match:
            w, h, hz = match.groups()
            result.append(dict(width=int(w), height=int(h), refresh=float(hz)))
    return result


def execute_hyprland(request):
    call, pid, signature = context(request['instance'])
    before = output(call)
    result = dict(compositor_pid=pid, signature=signature, monitor=before, modes=modes(before))
    if request['action'] == 'query':
        return result
    if request['action'] != 'apply':
        raise ValueError('Unsupported display action')
    if request['signature'] != signature:
        raise ValueError('Guest compositor changed during display fitting')
    fit = request['fit']
    mode = fit['mode']
    scale = fit['guest_scale']
    if mode not in modes(before) or type(scale) not in (int, float) or not math.isfinite(scale) or not 0.5 <= scale <= 8:
        raise ValueError('Display mode/scale is not admitted')
    # The pinned Lua compositor exposes hl.monitor; retain all other monitor
    # settings, including reserved panel space, from its existing output rule.
    code = 'hl.monitor({output=%s,mode="%dx%d@%.5f",scale="%.12f"})' % (
        json.dumps(before['name']), mode['width'], mode['height'], mode['refresh'], scale)
    reply = call(['eval', code])
    deadline = time.monotonic() + 8
    while True:
        after = output(call)
        if (after['width'], after['height']) == (mode['width'], mode['height']) and abs(after['scale']-scale) < 0.001:
            result.update(before=before, monitor=after, applied=True, control_reply=reply)
            return result
        if time.monotonic() >= deadline:
            raise RuntimeError('Guest did not acknowledge requested display mode/scale; observed ' + json.dumps(after))
        time.sleep(0.2)


def kwin_context(instance):
    instance = uuid.UUID(instance)
    spec = trusted('/run/wsx/' + instance.hex + '.json')
    if uuid.UUID(spec['instance_id']) != instance:
        raise ValueError('Guest display instance mismatch')
    user = pwd.getpwnam(spec['user'])
    if user.pw_uid == 0:
        raise ValueError('Non-root compositor required')
    executable = Path('/usr/lib/wsx/runtime/kwin-opaque/bin/kwin_wayland').resolve(strict=True)
    matches = []
    for proc in Path('/proc').glob('[0-9]*'):
        try:
            if proc.stat().st_uid != user.pw_uid or (proc/'exe').resolve(strict=True) != executable:
                continue
            env = dict(part.split('=', 1) for part in (proc/'environ').read_bytes().decode().split('\0') if '=' in part)
            if env.get('WSX_DESKTOP_INSTANCE') != str(instance):
                continue
            if env.get('KWIN_DRM_DEVICES') != spec['drm_node']:
                raise ValueError('KWin DRM device differs from the admitted instance')
            matches.append(proc)
        except (FileNotFoundError, ProcessLookupError):
            continue
    if len(matches) != 1:
        raise ValueError('No unique KWin process for the admitted instance')
    proc = matches[0]
    runtime = Path('/run/user') / str(user.pw_uid)
    inodes = set()
    for fd in (proc/'fd').iterdir():
        try:
            match = re.fullmatch(r'socket:\[(\d+)\]', os.readlink(fd))
            if match:
                inodes.add(match[1])
        except FileNotFoundError:
            continue
    sockets = set()
    for line in Path('/proc/net/unix').read_text().splitlines()[1:]:
        fields = line.split()
        if len(fields) != 8 or fields[6] not in inodes:
            continue
        path = Path(fields[7])
        if path.parent == runtime and re.fullmatch(r'wayland-[0-9]+', path.name):
            st = path.lstat()
            if st.st_uid != user.pw_uid or not stat.S_ISSOCK(st.st_mode):
                raise ValueError('Untrusted KWin Wayland socket')
            sockets.add(path.name)
    if len(sockets) != 1:
        raise ValueError('No unique Wayland socket owned by the admitted KWin')
    socket = next(iter(sockets))
    start = (proc/'stat').read_text().rsplit(')', 1)[1].split()[19]
    signature = 'kwin-' + proc.name + '-' + start + '-' + socket
    base = ['/usr/bin/runuser', '-u', user.pw_name, '--', '/usr/bin/env',
            'XDG_RUNTIME_DIR=' + str(runtime), 'WAYLAND_DISPLAY=' + socket,
            'DBUS_SESSION_BUS_ADDRESS=unix:path=' + str(runtime/'bus'),
            'XDG_SESSION_TYPE=wayland', 'QT_QPA_PLATFORM=wayland',
            'KSCREEN_BACKEND=KWayland', '/usr/bin/kscreen-doctor']
    def call(args):
        result = subprocess.run(base + args, capture_output=True, text=True, timeout=8)
        if result.returncode or len(result.stdout) > 1024*1024:
            raise RuntimeError('KWin display control failed: ' + result.stderr[:1024])
        return result.stdout
    return call, int(proc.name), signature


def kwin_output(value):
    enabled = [o for o in value['outputs'] if o.get('connected') and o.get('enabled', True)]
    if len(enabled) != 1:
        raise ValueError('Display fitting requires one active KWin output')
    output = enabled[0]
    if type(output['id']) is not int or output['id'] < 0 or output['rotation'] != 1:
        raise ValueError('Unsupported KWin output identity or rotation')
    current = [m for m in output['modes'] if m['id'] == output['currentModeId']]
    if len(current) != 1:
        raise ValueError('KWin current mode is unresolved')
    available = [dict(width=m['size']['width'], height=m['size']['height'], refresh=m['refreshRate']) for m in output['modes']]
    monitor = dict(name=output['name'], width=current[0]['size']['width'],
                   height=current[0]['size']['height'], scale=output['scale'])
    return output, monitor, available


def execute_kwin(request):
    call, pid, signature = kwin_context(request['instance'])
    raw, before, available = kwin_output(json.loads(call(['--json'])))
    result = dict(compositor='kwin', compositor_pid=pid, signature=signature, monitor=before, modes=available)
    if request['action'] == 'query':
        return result
    if request['action'] != 'apply' or request['signature'] != signature:
        raise ValueError('Display action or KWin instance changed')
    mode, scale = request['fit']['mode'], request['fit']['guest_scale']
    if mode not in available or type(scale) not in (int, float) or not math.isfinite(scale) or not 0.5 <= scale <= 8:
        raise ValueError('KWin display mode/scale is not admitted')
    matching = [m for m in raw['modes'] if dict(width=m['size']['width'], height=m['size']['height'], refresh=m['refreshRate']) == mode]
    mode_id = matching[0]['id']
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', mode_id):
        raise ValueError('Unsupported KScreen mode identity')
    prefix = 'output.' + str(raw['id'])
    reply = call([prefix + '.mode.' + mode_id, prefix + '.scale.' + format(scale, '.12f')])
    deadline = time.monotonic() + 8
    while True:
        _, after, _ = kwin_output(json.loads(call(['--json'])))
        if (after['width'], after['height']) == (mode['width'], mode['height']) and abs(after['scale']-scale) < 0.001:
            result.update(before=before, monitor=after, applied=True, control_reply=reply)
            return result
        if time.monotonic() >= deadline:
            raise RuntimeError('KWin did not acknowledge the requested mode/scale')
        time.sleep(0.2)


def execute(request):
    manifest = Path('/usr/lib/wsx/runtime/kwin-opaque/manifest.json')
    if manifest.exists():
        if trusted(manifest, 2 * 1024 * 1024).get('abi') != 2:
            raise ValueError('Unsupported KWin display ABI')
        return execute_kwin(request)
    return execute_hyprland(request)


if __name__ == '__main__':
    print(json.dumps(execute(json.load(sys.stdin))))
