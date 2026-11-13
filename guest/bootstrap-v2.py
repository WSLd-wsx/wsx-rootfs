# Original WSX code, PolyForm-Noncommercial-1.0.0. See LICENSE-MAP.md.
"""WSX Guest bootstrap v2: constrained adapter storage and pinned dispatch."""
import json
import os
from pathlib import Path
import re
import runpy
import sys
import uuid

PROTOCOL = 'wsx-guest-bootstrap'
MAJOR = 2
MAX_REQUEST = 12 * 1024 * 1024
STORE = Path('/var/lib/wsx/guest-adapters')


def dispatch(store, adapter_store, profile_path, operation, instance):
    """Return only a fixed adapter command after verifying its session pin.

    This routing primitive does not prove session start or GPU retirement.
    """
    if operation not in ('host-call', 'prepare', 'start'):
        raise ValueError('Unsupported adapter entry operation')
    instance = uuid.UUID(instance)
    if not instance.int: raise ValueError('Invalid session identity')
    profile = json.loads(adapter_store['_read_regular'](profile_path, 65536))
    if (not isinstance(profile, dict) or type(profile.get('schema_version')) is not int
            or profile['schema_version'] != 1 or profile.get('implementation') not in ('hyprland', 'plasma')):
        raise ValueError('Invalid Guest desktop profile')
    pin = adapter_store['session_pin'](store, str(instance), profile['implementation'])
    entry = str(store / pin['sha256'] / 'wsx-guest.py')
    args = ['/usr/bin/python3', '-I', entry, operation]
    if operation == 'start': args.extend(['--instance', str(instance)])
    return args


def handle(request, store, adapter_store, profile_path=Path('/usr/lib/wsx/guest-profile.json')):
    request_id = request.get('id') if isinstance(request, dict) else None
    safe_id = request_id if isinstance(request_id, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,96}', request_id) else None
    reply = dict(protocol=PROTOCOL, major=MAJOR, id=safe_id)
    try:
        if not isinstance(request, dict) or set(request) != {'protocol', 'major', 'id', 'operation', 'params'}:
            raise ValueError('Invalid request fields')
        if request['protocol'] != PROTOCOL or type(request['major']) is not int or request['major'] != MAJOR:
            raise ValueError('Unsupported bootstrap protocol')
        if not isinstance(request_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,96}', request_id):
            raise ValueError('Invalid request identifier')
        params = request['params']
        if not isinstance(params, dict): raise ValueError('Invalid parameters')
        if request['operation'] == 'capabilities':
            if params: raise ValueError('Unexpected capabilities parameters')
            result = dict(bootstrap_major=MAJOR, adapter_protocol_major=2,
                          operations=['capabilities', 'adapter.stage', 'adapter.inspect', 'adapter.select', 'session.pin', 'session.inspect'],
                          dispatch_supported=True, activation_supported=True)
        elif request['operation'] == 'adapter.stage':
            if set(params) != {'manifest', 'expected_sha256', 'files'} or not isinstance(params['manifest'], str):
                raise ValueError('Invalid adapter stage parameters')
            result = adapter_store['stage'](store, params['manifest'].encode('utf-8'), params['expected_sha256'], params['files'])
        elif request['operation'] == 'adapter.inspect':
            if set(params) != {'sha256'} or not isinstance(params['sha256'], str) or not re.fullmatch(r'[0-9a-f]{64}', params['sha256']):
                raise ValueError('Invalid adapter identity')
            manifest = adapter_store['verify'](store / params['sha256'], params['sha256'])
            result = dict(sha256=params['sha256'], implementation=manifest['implementation'], integrity_verified=True, publisher_verified=False)
        elif request['operation'] in ('adapter.select', 'session.pin', 'session.inspect'):
            # The image profile, rather than a caller-provided desktop name,
            # determines which adapter implementation can be used.
            profile = json.loads(adapter_store['_read_regular'](profile_path, 65536))
            if not isinstance(profile, dict) or type(profile.get('schema_version')) is not int or profile['schema_version'] != 1 or profile.get('implementation') not in ('hyprland', 'plasma'):
                raise ValueError('Invalid Guest desktop profile')
            implementation = profile['implementation']
            if request['operation'] == 'adapter.select':
                if set(params) != {'sha256'}: raise ValueError('Invalid adapter selection parameters')
                result = adapter_store['select'](store, params['sha256'], implementation)
            elif request['operation'] == 'session.pin':
                if set(params) != {'instance', 'sha256'} or not isinstance(params['instance'], str) or not isinstance(params['sha256'], str) or not re.fullmatch(r'[0-9a-f]{64}', params['sha256']):
                    raise ValueError('Invalid session pin parameters')
                result = adapter_store['pin_session'](store, params['instance'], implementation, params['sha256'])
            else:
                if set(params) != {'instance'} or not isinstance(params['instance'], str): raise ValueError('Invalid session inspection parameters')
                result = adapter_store['session_pin'](store, params['instance'], implementation)
        else:
            raise ValueError('Unsupported bootstrap operation')
        reply.update(ok=True, result=result)
    except (ValueError, TypeError, KeyError, OSError) as exc:
        reply.update(ok=False, error=dict(code='bootstrap_rejected', message=str(exc)[:1024]))
    return reply


def main():
    if os.geteuid() != 0: raise SystemExit('Root control channel required')
    adapter_store = runpy.run_path('/usr/lib/wsx/adapter-store.py')
    adapter_store['_trusted_dir'](STORE.parent)
    STORE.mkdir(mode=0o700, exist_ok=True)
    adapter_store['_trusted_dir'](STORE)
    if len(sys.argv) > 1:
        if len(sys.argv) != 5 or sys.argv[1] != 'dispatch' or sys.argv[3] != '--instance':
            raise SystemExit('Invalid bootstrap dispatch arguments')
        try:
            args = dispatch(STORE, adapter_store, Path('/usr/lib/wsx/guest-profile.json'), sys.argv[2], sys.argv[4])
        except (ValueError, TypeError, KeyError, OSError) as exc:
            raise SystemExit('Bootstrap dispatch rejected: ' + str(exc)) from exc
        os.execve(args[0], args, {'PATH': '/usr/bin:/bin'})
    raw = sys.stdin.buffer.read(MAX_REQUEST + 1)
    if len(raw) > MAX_REQUEST: raise SystemExit('Bootstrap request exceeds limit')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result: raise ValueError('Duplicate request key')
            result[key] = value
        return result
    try:
        request = json.loads(raw, object_pairs_hook=unique)
    except (ValueError, UnicodeError):
        request = None
    reply = handle(request, STORE, adapter_store)
    print(json.dumps(reply, separators=(',', ':'), ensure_ascii=True))


if __name__ == '__main__': main()
