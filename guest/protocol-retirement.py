# SPDX-License-Identifier: MIT
# Adapted from the verified wsld Native Guest retirement helper.
# Copyright (c) 2026 WGY (GitHub: wgy-wsx) <wgy@wsxdesk.com>
from pathlib import Path
import re
import subprocess
import time
import json
import pwd

TIMINGS = []

def run(argv, **kwargs):
    start = time.monotonic()
    try:
        return subprocess.run(argv, **kwargs)
    finally:
        TIMINGS.append(dict(operation=Path(argv[0]).name + " " + argv[1],
                            elapsed_ms=round((time.monotonic()-start)*1000, 3)))

def instance_processes(instance):
    marker = ('WSX_DESKTOP_INSTANCE=' + str(instance)).encode()
    rows = []
    for process in Path('/proc').glob('[0-9]*'):
        try:
            if marker in (process / 'environ').read_bytes().split(b'\0'):
                rows.append(dict(pid=int(process.name), name=(process/'comm').read_text().strip(),
                                 cgroup=(process/'cgroup').read_text().strip()))
        except (FileNotFoundError, ProcessLookupError):
            continue
    return rows


def wait_session_drain(instance, timeout=15):
    # loginctl termination is asynchronous. Keep Native servicing queues while
    # waiting; a timeout preserves ownership and never kills residual processes.
    started = time.monotonic()
    deadline = started + timeout
    previous = None
    while True:
        rows = instance_processes(instance)
        seat = Path('/run/seatd.sock').exists()
        owner = (Path('/run/wsx')/(instance.hex+'.owner.json')).exists()
        state = dict(processes=rows[:32], seat_present=seat, owner_present=owner)
        if state != previous:
            TIMINGS.append(dict(operation='session_drain', elapsed_ms=round((time.monotonic()-started)*1000, 3), **state))
            previous = state
        if not rows and not seat and not owner:
            return
        if time.monotonic() >= deadline:
            raise RuntimeError('Session drain incomplete: ' + json.dumps(dict(
                instance=str(instance), processes=rows[:32], seat_present=seat,
                owner_present=owner), sort_keys=True))
        time.sleep(0.05)


def owned_user_units(instance, proc=Path('/proc')):
    marker = ('WSX_DESKTOP_INSTANCE=' + str(instance)).encode()
    groups = {}
    for process in proc.glob('[0-9]*'):
        try:
            group = (process/'cgroup').read_text().strip().removeprefix('0::')
            tagged = marker in (process/'environ').read_bytes().split(b'\0')
            groups.setdefault(group, []).append((process, tagged))
        except (FileNotFoundError, ProcessLookupError):
            continue
    units = []
    for group, members in groups.items():
        if not any(tagged for _, tagged in members):
            continue
        match = re.fullmatch(
            r'/user.slice/user-(\d+)\.slice/user@\1\.service/'
            r'(?:session.slice|app.slice)(?:/[^/]+)*/([^/]+\.(?:service|scope))', group)
        if not match:
            continue
        subtree = [entry for name, rows in groups.items()
                   if name == group or name.startswith(group + '/') for entry in rows]
        if not all(tagged for _, tagged in subtree):
            raise RuntimeError('User unit contains another session: ' + match[2])
        units.append((int(match[1]), match[2], group, subtree))
    return units


def stop_owned_user_units(instance):
    # Desktop logout can leave D-Bus activated accessibility/settings services
    # outside the session scope. Retire only units wholly tagged by this instance.
    marker = ('WSX_DESKTOP_INSTANCE=' + str(instance)).encode()
    for uid, unit, group, members in owned_user_units(instance):
        for process, _ in members:
            try:
                if (process/'cgroup').read_text().strip().removeprefix('0::') != group or marker not in (process/'environ').read_bytes().split(b'\0'):
                    raise RuntimeError('User unit ownership changed before stop: ' + unit)
            except (FileNotFoundError, ProcessLookupError):
                continue
        account = pwd.getpwuid(uid)
        run(['/usr/bin/systemctl', '--user', '--machine=' + account.pw_name + '@.host',
             'stop', '--', unit], check=True, capture_output=True, text=True, timeout=20)


def stop_unit(unit):
    result = run(['/usr/bin/systemctl', 'stop', unit], capture_output=True, text=True)
    # Transient units can disappear between the load query and stop. Only a
    # successful state query proving inactivity reconciles that race.
    state = run(['/usr/bin/systemctl', 'show', unit,
        '--property=ActiveState', '--value'], check=True, capture_output=True, text=True)
    if state.stdout.strip() not in ('inactive', 'failed'):
        raise RuntimeError('Session unit remains active: ' + unit + '; stop_exit=' + str(result.returncode))


def stop_plasma(instance):
    unit = 'wsx-cachyos-plasma-' + instance.hex + '.service'
    state = run(['/usr/bin/systemctl', 'show', '--property=LoadState',
                            '--value', unit], check=True, text=True, capture_output=True)
    if state.stdout.strip() == 'not-found':
        return False
    if state.stdout.strip() != 'loaded':
        raise RuntimeError('Plasma session unit is unresolved during retirement')
    # Guest validates the root-owned instance descriptor and requests normal
    # Plasma logout, then waits for the compositor, input and seat in order.
    run(['/usr/bin/wsx-guest', 'stop', '--instance', str(instance)], check=True)
    state = run(['/usr/bin/systemctl', 'show', unit,
                            '--property=ActiveState', '--value'],
                           check=True, text=True, capture_output=True)
    if state.stdout.strip() not in ('inactive', 'failed'):
        raise RuntimeError('Plasma session did not stop normally; device retained')
    stop_owned_user_units(instance)
    wait_session_drain(instance)
    print('WSX_PLASMA_SESSION_RETIRED instance=' + str(instance), flush=True)
    return True



def stop_session(instance):
    TIMINGS.clear()
    started = time.monotonic()
    if not stop_plasma(instance):
        unit = f'wsx-omarchy-{instance.hex}.service'
        # PAM moves the compositor out of the service cgroup into a logind scope.
        # Stop only sessions whose live processes carry this exact instance marker.
        # Never terminate all sessions of the desktop user.
        sessions = set()
        marker = ('WSX_DESKTOP_INSTANCE=' + str(instance)).encode()
        for process in Path('/proc').glob('[0-9]*'):
            try:
                if marker not in (process / 'environ').read_bytes().split(b'\0'):
                    continue
                for line in (process / 'cgroup').read_text().splitlines():
                    match = re.fullmatch(r'0::/user.slice/user-(\d+).slice/session-([A-Za-z0-9]+)\.scope', line)
                    if match:
                        sessions.add((match[1], match[2]))
            except (FileNotFoundError, ProcessLookupError, PermissionError):
                continue
        for uid, session in sorted(sessions):
            actual = run(['/usr/bin/loginctl', 'show-session', session,
                '--property=User', '--value'], check=True, text=True, capture_output=True)
            if actual.stdout.strip() != uid:
                raise RuntimeError('PAM session owner changed during retirement')
            run(['/usr/bin/loginctl', 'terminate-session', session], check=True)
        state = run(['/usr/bin/systemctl', 'show', '--property=LoadState',
                                '--value', unit], check=True, text=True, capture_output=True)
        if state.stdout.strip() != 'not-found':
            stop_unit(unit)
        stop_owned_user_units(instance)
        wait_session_drain(instance)

    return dict(total_ms=round((time.monotonic()-started)*1000, 3), commands=list(TIMINGS))
