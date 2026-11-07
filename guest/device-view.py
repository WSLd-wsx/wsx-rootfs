# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Expose only this distro's admitted DRM device to its graphics userspace."""
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import time
import uuid

ROOT = Path('/run/wsx-device-view')

def mounts():
    result = {}
    for line in Path('/proc/self/mountinfo').read_text().splitlines():
        fields = line.split(); split = fields.index('-')
        result[fields[4]] = dict(source=fields[split+2], filesystem=fields[split+1])
    return result


def selected_nodes(instance, card, sys=Path('/sys')):
    instance = uuid.UUID(str(instance))
    if not re.fullmatch(r'/dev/dri/card[0-9]+', card):
        raise ValueError('Expected an admitted DRM primary node')
    entry = sys/'class/drm'/Path(card).name
    actual = entry.resolve(strict=True)
    associated = False
    for parent in actual.parents:
        subsystem = parent/'subsystem'
        if subsystem.is_symlink() and subsystem.resolve().name == 'vmbus':
            associated = uuid.UUID((parent/'device_id').read_text().strip().strip('{}')) == instance
            break
    if not associated:
        raise ValueError('DRM node belongs to another Host instance')
    nodes = {}
    for p in (sys/'class/drm').iterdir():
        if not re.fullmatch(r'(?:card|renderD)[0-9]+', p.name):
            continue
        if p.resolve(strict=True).parent != actual.parent:
            continue
        major, minor = map(int, (p/'dev').read_text().strip().split(':'))
        if major != 226 or minor < 0:
            raise ValueError('Unexpected DRM device number')
        nodes[p.name] = os.makedev(major, minor)
    if Path(card).name not in nodes or len(nodes) != 2 or sum(n.startswith('renderD') for n in nodes) != 1:
        raise ValueError('Expected one primary and one render node for the exact Owner')
    return nodes


def selected_input_nodes(instance, sys=Path('/sys')):
    instance = uuid.UUID(str(instance))
    expected = {'WSX ' + str(instance) + ' ' + kind for kind in ('Keyboard', 'Pointer', 'Wheel')}
    nodes = {}
    for event in (sys/'class/input').glob('event[0-9]*'):
        try:
            name = (event/'device/name').read_text().strip()
            if name not in expected:
                continue
            major, minor = map(int, (event/'dev').read_text().strip().split(':'))
            if major != 13 or minor < 0:
                raise ValueError('Unexpected input device number')
            if name in nodes:
                raise ValueError('Duplicate instance input device')
            nodes[name] = (event.name, os.makedev(major, minor))
        except FileNotFoundError:
            continue
    if set(nodes) != expected:
        raise ValueError('Expected all three instance input devices')
    return dict(nodes[name] for name in sorted(nodes))


def prepare_input(instance):
    instance = uuid.UUID(str(instance))
    nodes = selected_input_nodes(instance)
    if os.geteuid() != 0 or os.stat('/proc/self/ns/mnt').st_ino != os.stat('/proc/1/ns/mnt').st_ino:
        raise RuntimeError('Input view requires the distro init mount namespace')
    result = subprocess.run(['/usr/bin/systemctl', 'show', 'systemd-logind.service',
                             '--property=MainPID', '--value'], check=True,
                            capture_output=True, text=True, timeout=10)
    logind = int(result.stdout.strip())
    if logind <= 1 or (Path('/proc')/str(logind)/'exe').resolve(strict=True).name != 'systemd-logind':
        raise RuntimeError('Cannot establish logind input monitor identity')
    deadline = time.monotonic() + 2
    while True:
        clients = []
        for process in Path('/proc').glob('[0-9]*'):
            for fd in (process/'fd').glob('*'):
                try:
                    info = fd.stat()
                    if stat.S_ISCHR(info.st_mode) and os.major(info.st_rdev) == 13 and int(process.name) != logind:
                        clients.append(dict(pid=int(process.name), name=(process/'comm').read_text().strip(),
                                            minor=os.minor(info.st_rdev)))
                except (FileNotFoundError, ProcessLookupError):
                    pass
        if not clients:
            break
        if time.monotonic() >= deadline:
            raise RuntimeError('Existing Guest input client must retire before view replacement: ' + json.dumps(clients[:32]))
        time.sleep(0.05)
    info = ROOT.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o077:
        raise RuntimeError('Unsafe device view state directory')
    target = Path('/dev/input')
    if target.is_symlink() or not target.is_dir():
        raise RuntimeError('Unsafe input directory')
    current = mounts()
    record = ROOT/'input-record.json'
    if str(target) in current:
        previous = uuid.UUID(json.loads(record.read_text())['instance'])
        source = ROOT/('input-' + previous.hex)/'input'
        if current[str(target)] != dict(source='wsx-input:'+str(previous), filesystem='tmpfs'):
            raise RuntimeError('Existing input mount is not WSX-owned')
        subprocess.run(['mount', '--make-private', str(target)], check=True)
        subprocess.run(['umount', str(target)], check=True)
        subprocess.run(['umount', str(source)], check=True)
        source.rmdir(); source.parent.rmdir(); record.unlink()
    source = ROOT/('input-' + instance.hex)/'input'
    source.mkdir(parents=True, mode=0o700, exist_ok=False)
    subprocess.run(['mount', '-t', 'tmpfs', '-o', 'mode=0755,nosuid,size=64k',
                    'wsx-input:'+str(instance), str(source)], check=True)
    for name, device in nodes.items():
        os.mknod(source/name, stat.S_IFCHR | 0o600, device)
    subprocess.run(['mount', '--bind', str(source), str(target)], check=True)
    subprocess.run(['mount', '--make-private', str(target)], check=True)
    temporary = ROOT/'.input-record-new'
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(dict(instance=str(instance), nodes=sorted(nodes)), stream)
        stream.flush(); os.fsync(stream.fileno())
    os.replace(temporary, record)
    return ['/dev/input/' + name for name in sorted(nodes)]


def prepare(instance, card):
    instance = uuid.UUID(str(instance))
    nodes = selected_nodes(instance, card)
    if os.geteuid() != 0 or os.stat('/proc/self/ns/mnt').st_ino != os.stat('/proc/1/ns/mnt').st_ino:
        raise RuntimeError('Device view requires the distro init mount namespace')
    for process in Path('/proc').glob('[0-9]*'):
        for fd in (process/'fd').glob('*'):
            try:
                info = fd.stat()
                if stat.S_ISCHR(info.st_mode) and os.major(info.st_rdev) == 226:
                    raise RuntimeError('Existing Guest DRM client must retire before device view replacement')
            except (FileNotFoundError, ProcessLookupError):
                pass
    ROOT.mkdir(mode=0o700, exist_ok=True)
    info = ROOT.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o077:
        raise RuntimeError('Unsafe device view state directory')
    target = Path('/dev/dri')
    if target.is_symlink() or not target.is_dir():
        raise RuntimeError('Unsafe DRM directory')
    current = mounts()
    record = ROOT/'record.json'
    if str(target) in current:
        old = json.loads(record.read_text())
        previous = uuid.UUID(old['instance'])
        source = ROOT/previous.hex/'dri'
        if current[str(target)] != dict(source='wsx-dri:'+str(previous), filesystem='tmpfs'):
            raise RuntimeError('Existing DRM mount is not WSX-owned')
        subprocess.run(['mount', '--make-private', str(target)], check=True)
        subprocess.run(['umount', str(target)], check=True)
        subprocess.run(['umount', str(source)], check=True)
        source.rmdir(); source.parent.rmdir(); record.unlink()
    # Receive parent device mounts but never propagate our view to peer distros.
    subprocess.run(['mount', '--make-slave', '/dev'], check=True)
    subprocess.run(['mount', '--make-slave', '/run'], check=True)
    source = ROOT/instance.hex/'dri'
    source.mkdir(parents=True, mode=0o700, exist_ok=False)
    subprocess.run(['mount', '-t', 'tmpfs', '-o', 'mode=0755,nosuid,size=64k',
                    'wsx-dri:'+str(instance), str(source)], check=True)
    for name, device in nodes.items():
        os.mknod(source/name, stat.S_IFCHR | 0o600, device)
    subprocess.run(['mount', '--bind', str(source), str(target)], check=True)
    subprocess.run(['mount', '--make-private', str(target)], check=True)
    temporary = ROOT/'.record-new'
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(dict(instance=str(instance), nodes=sorted(nodes)), stream)
        stream.flush(); os.fsync(stream.fileno())
    os.replace(temporary, record)
    return dict(instance=str(instance), nodes=sorted(nodes), scope='distro-local DRM view')
