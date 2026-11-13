# Original WSX code, PolyForm-Noncommercial-1.0.0. See LICENSE-MAP.md.
"""Bounded, content-addressed Guest adapter storage; no arbitrary command endpoint.

Callers must authenticate the expected manifest digest independently. A digest
provided alongside an untrusted bundle does not authenticate its publisher.
"""
import base64
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import tempfile

MAX_MANIFEST = 65536
MAX_FILE = 2 * 1024 * 1024
MAX_TOTAL = 8 * 1024 * 1024
FILES = frozenset(('protocol.py', 'desktop.py', 'display.py', 'retirement.py', 'device-view.py', 'wsx-guest.py'))


def _trusted_dir(path):
    p = Path(path)
    info = p.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o022:
        raise ValueError('Untrusted adapter directory')
    return p


def _manifest(raw, expected):
    if not isinstance(raw, bytes) or len(raw) > MAX_MANIFEST or not isinstance(expected, str) or not re.fullmatch(r'[0-9a-f]{64}', expected):
        raise ValueError('Invalid adapter manifest or trusted digest')
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError('Adapter manifest digest differs from trusted catalog')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result: raise ValueError('Duplicate adapter manifest key')
            result[key] = value
        return result
    data = json.loads(raw, object_pairs_hook=unique)
    if not isinstance(data, dict): raise ValueError('Invalid adapter manifest')
    if set(data) != {'schema_version', 'kind', 'protocol_major', 'implementation', 'files'}:
        raise ValueError('Unknown adapter manifest fields')
    if type(data['schema_version']) is not int or data['schema_version'] != 1 or data['kind'] != 'wsx-guest-adapter' or type(data['protocol_major']) is not int or data['protocol_major'] != 2:
        raise ValueError('Unsupported adapter contract')
    if data['implementation'] not in ('hyprland', 'plasma') or not isinstance(data['files'], dict) or set(data['files']) != FILES:
        raise ValueError('Invalid adapter implementation or file set')
    total = 0
    for item in data['files'].values():
        if not isinstance(item, dict) or set(item) != {'sha256', 'bytes'} or not isinstance(item['sha256'], str) or not re.fullmatch(r'[0-9a-f]{64}', item['sha256']):
            raise ValueError('Invalid adapter file digest')
        size = item['bytes']
        if type(size) is not int or not 0 < size <= MAX_FILE:
            raise ValueError('Invalid adapter file size')
        total += size
    if total > MAX_TOTAL:
        raise ValueError('Adapter bundle exceeds limit')
    return data


def _read_regular(path, limit):
    fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o022 or info.st_size > limit:
            raise ValueError('Untrusted adapter file')
        return stream.read(limit + 1)


def verify(directory, expected):
    directory = _trusted_dir(directory)
    raw = _read_regular(directory / 'manifest.json', MAX_MANIFEST)
    manifest = _manifest(raw, expected)
    if {p.name for p in directory.iterdir()} != FILES | {'manifest.json'}:
        raise ValueError('Unexpected adapter directory contents')
    for name, item in manifest['files'].items():
        data = _read_regular(directory / name, MAX_FILE)
        if len(data) != item['bytes'] or hashlib.sha256(data).hexdigest() != item['sha256']:
            raise ValueError('Adapter file differs from manifest: ' + name)
    return manifest


def stage(store, manifest_raw, expected, encoded_files):
    """Write a new immutable-by-convention version without changing selection."""
    store = _trusted_dir(store)
    manifest = _manifest(manifest_raw, expected)
    if not isinstance(encoded_files, dict) or set(encoded_files) != FILES:
        raise ValueError('Incomplete adapter payload')
    data = {}
    for name, item in manifest['files'].items():
        if not isinstance(encoded_files[name], str) or len(encoded_files[name]) > ((MAX_FILE + 2) // 3) * 4:
            raise ValueError('Encoded adapter payload exceeds limit')
        try:
            data[name] = base64.b64decode(encoded_files[name], validate=True)
        except (ValueError, TypeError) as exc:
            raise ValueError('Invalid adapter payload: ' + name) from exc
        if len(data[name]) != item['bytes'] or hashlib.sha256(data[name]).hexdigest() != item['sha256']:
            raise ValueError('Adapter payload differs from manifest: ' + name)
    with _locked(store):
        target = store / expected
        if target.exists() or target.is_symlink():
            verify(target, expected)
            return {'digest': expected, 'staged': False}
        temporary = Path(tempfile.mkdtemp(prefix='.staging-', dir=store))
        try:
            for name, content in [('manifest.json', manifest_raw), *data.items()]:
                fd = os.open(temporary / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
                with os.fdopen(fd, 'wb') as output:
                    output.write(content); output.flush(); os.fsync(output.fileno())
            verify(temporary, expected)
            directory_fd = os.open(temporary, os.O_RDONLY | os.O_DIRECTORY)
            try: os.fsync(directory_fd)
            finally: os.close(directory_fd)
            os.rename(temporary, target)
            fd = os.open(store, os.O_RDONLY | os.O_DIRECTORY)
            try: os.fsync(fd)
            finally: os.close(fd)
        finally:
            if temporary.exists(): shutil.rmtree(temporary)
    return {'digest': expected, 'staged': True}


def _locked(store):
    """Open the root-owned store lock; callers must keep the returned file open."""
    store = _trusted_dir(store)
    fd = os.open(store / '.lock', os.O_RDWR | os.O_CREAT | os.O_CLOEXEC | os.O_NOFOLLOW, 0o600)
    stream = os.fdopen(fd, 'a+b')
    info = os.fstat(stream.fileno())
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o077:
        stream.close()
        raise ValueError('Untrusted adapter store lock')
    fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
    return stream


def _sync_dir(directory):
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try: os.fsync(fd)
    finally: os.close(fd)


def _selection(store):
    raw = _read_regular(store / 'active.json', MAX_MANIFEST)
    data = json.loads(raw)
    if not isinstance(data, dict) or set(data) != {'schema_version', 'sha256'} or type(data['schema_version']) is not int or data['schema_version'] != 1 or not isinstance(data['sha256'], str) or not re.fullmatch(r'[0-9a-f]{64}', data['sha256']):
        raise ValueError('Invalid adapter selection')
    return data['sha256']


def select(store, expected, implementation):
    """Select a staged version for future sessions; existing pins are untouched.

    The caller must independently authenticate the catalog and verify the
    Guest's actual desktop implementation before invoking this operation.
    """
    store = _trusted_dir(store)
    if not isinstance(expected, str) or not re.fullmatch(r'[0-9a-f]{64}', expected):
        raise ValueError('Invalid adapter identity')
    with _locked(store):
        manifest = verify(store / expected, expected)
        if manifest['implementation'] != implementation:
            raise ValueError('Adapter desktop implementation mismatch')
        pointer = store / 'active.json'
        if pointer.exists() or pointer.is_symlink(): _selection(store)
        fd, temporary = tempfile.mkstemp(prefix='.selection-', dir=store)
        try:
            with os.fdopen(fd, 'w') as stream:
                json.dump({'schema_version': 1, 'sha256': expected}, stream, sort_keys=True)
                stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
            os.replace(temporary, pointer)
            _sync_dir(store)
        finally:
            if os.path.exists(temporary): os.unlink(temporary)
    return {'selected': expected}


def pin_session(store, instance, implementation, expected=None):
    """Record one session's selection; never remove a pin implicitly."""
    import uuid
    store = _trusted_dir(store)
    instance = uuid.UUID(str(instance))
    if not instance.int: raise ValueError('Invalid session identity')
    with _locked(store):
        digest = _selection(store)
        if expected is not None and digest != expected:
            raise ValueError('Adapter selection changed before session pin')
        manifest = verify(store / digest, digest)
        if manifest['implementation'] != implementation:
            raise ValueError('Adapter desktop implementation mismatch')
        path = store / ('session-' + instance.hex + '.json')
        fd, temporary = tempfile.mkstemp(prefix='.session-', dir=store)
        try:
            with os.fdopen(fd, 'w') as stream:
                json.dump({'schema_version': 1, 'instance': str(instance), 'sha256': digest}, stream, sort_keys=True)
                stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
            # Publish without replacing an existing session pin.
            os.link(temporary, path, follow_symlinks=False)
            _sync_dir(store)
        finally:
            os.unlink(temporary)
    return {'instance': str(instance), 'sha256': digest}


def session_pin(store, instance, implementation):
    """Read an exact pinned version and verify its bytes before each use."""
    import uuid
    store = _trusted_dir(store)
    instance = uuid.UUID(str(instance))
    if not instance.int: raise ValueError('Invalid session identity')
    with _locked(store):
        raw = _read_regular(store / ('session-' + instance.hex + '.json'), MAX_MANIFEST)
        data = json.loads(raw)
        if (not isinstance(data, dict) or set(data) != {'schema_version', 'instance', 'sha256'}
                or type(data['schema_version']) is not int or data['schema_version'] != 1
                or data['instance'] != str(instance) or not isinstance(data['sha256'], str)
                or not re.fullmatch(r'[0-9a-f]{64}', data['sha256'])):
            raise ValueError('Invalid session adapter pin')
        manifest = verify(store / data['sha256'], data['sha256'])
        if manifest['implementation'] != implementation:
            raise ValueError('Adapter desktop implementation mismatch')
        return {'instance': str(instance), 'sha256': data['sha256']}
