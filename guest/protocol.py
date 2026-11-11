"""WSX Guest/Host protocol 1.0; Guest owns desktop implementation details.

Original WSX code, PolyForm-Noncommercial-1.0.0. See LICENSE-MAP.md.
No GPU or kernel retirement is implied by a session acknowledgement.
"""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import pwd
import re
import runpy
import stat
import subprocess
import sys
import uuid

MAJOR, MINOR = 1, 0
LIMIT = 1024 * 1024
CAPABILITIES = ['account.status', 'desktop.preflight', 'session.status', 'session.stop',
                'display.query', 'display.apply', 'lifecycle.cli-v1',
                'graphics.distro-device-view-v1', 'graphics.distro-input-view-v1',
                'graphics.linear-preflight-v1']
PROFILE = Path('/usr/lib/wsx/guest-profile.json')
RUNTIME = Path('/usr/lib/wsx/runtime')


class ProtocolError(Exception):
    def __init__(self, code, message, retryable=False):
        super().__init__(message)
        self.code, self.retryable = code, retryable


def trusted(path, limit=2 * 1024 * 1024):
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC), 'rb') as stream:
        st = os.fstat(stream.fileno())
        if not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or st.st_mode & 0o022 or st.st_size > limit:
            raise ProtocolError('untrusted_metadata', 'Guest metadata ownership, mode or size is invalid')
        raw = stream.read(limit + 1)
        if len(raw) > limit:
            raise ProtocolError('invalid_request', 'Guest metadata exceeds limit')
        return raw


def profile():
    raw = trusted(PROFILE)
    value = json.loads(raw)
    if value.get('schema_version') != 1:
        raise ProtocolError('incompatible_profile', 'Unsupported Guest profile schema')
    return value, hashlib.sha256(raw).hexdigest()


def account_status():
    try:
        initialized = json.loads(trusted('/var/lib/wsx/initialized.json', 65536))
    except FileNotFoundError:
        return dict(initialized=False, initialization='not_found')
    user = pwd.getpwnam(initialized['user'])
    if user.pw_uid == 0:
        raise ProtocolError('invalid_account', 'A non-root desktop account is required')
    return dict(initialized=True, user=user.pw_name, uid=user.pw_uid,
                timezone=initialized.get('timezone'), guest_interface_abi=1)


def preflight(params, guest):
    spec, digest = profile()
    contract = params['contract']
    if digest != contract['guest_profile_sha256']:
        raise ProtocolError('profile_mismatch', 'Installed Guest profile differs from the release')
    if contract['sharing_path'] != 'opaque-v1' or contract['producer_abi'] != 1 or contract['consumer_abi'] != 2:
        raise ProtocolError('unsupported_graphics', 'Guest cannot satisfy the requested graphics protocol')
    requested = params.get('requested_sharing_path', 'opaque-v1')
    if requested not in ('opaque-v1', 'linear-v1'):
        raise ProtocolError('unsupported_graphics', 'Requested Guest sharing path is unavailable')
    manifests = {}
    for name, expected in spec['component_manifests'].items():
        if not re.fullmatch(r'[a-z0-9-]+', name):
            raise ProtocolError('invalid_profile', 'Invalid internal component identifier')
        directory = RUNTIME / name
        raw = trusted(directory / 'manifest.json')
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ProtocolError('component_mismatch', 'Installed component manifest differs from Guest profile')
        component = json.loads(raw)
        if not component.get('files'):
            raise ProtocolError('component_mismatch', 'Empty component closure')
        for relative, digest in component['files'].items():
            target = (directory / relative).resolve(strict=True)
            if not target.is_relative_to(directory) or not target.is_file():
                raise ProtocolError('component_mismatch', 'Component path escapes its closure')
            with target.open('rb') as stream:
                if hashlib.file_digest(stream, 'sha256').hexdigest() != digest:
                    raise ProtocolError('component_mismatch', 'Installed component bytes changed')
        manifests[name] = component
    mesa, venus, consumer = (manifests[n] for n in ('mesa', 'venus', spec['consumer']))
    if requested == 'opaque-v1':
        if not (mesa.get('opaque_consumer') and mesa.get('opaque_gbm_export') and
                not mesa.get('presentation_staging_policy') and venus.get('opaque_wsi') and
                venus.get('opaque_import') and consumer.get('abi') == 2):
            raise ProtocolError('unsupported_graphics', 'Required opaque capabilities are unavailable')
    elif not (mesa.get('linear_shared_compat') is True and
              mesa.get('presentation_staging_policy') is False and
              venus.get('direct_wsi') == 'linear-v1' and consumer.get('abi') == 2 and
              (spec['implementation'] != 'hyprland' or mesa.get('linear_modifier_feedback') is True)):
        raise ProtocolError('unsupported_graphics', 'Required LINEAR Guest capabilities are unavailable')
    if spec['implementation'] == 'plasma':
        expected = json.loads(trusted('/usr/lib/wsx/plasma-compat.json', 65536))['packages']
        actual = subprocess.run(['/usr/bin/pacman', '-Q', 'kwin', 'plasma-workspace', 'qt6-base'],
                                check=True, capture_output=True, text=True, timeout=10)
        versions = dict(line.split(' ', 1) for line in actual.stdout.splitlines())
        # Internal call stays entirely within the Guest-owned implementation.
        guest['check_plasma_compatibility'](Path('/proc/cpuinfo').read_text(), versions, expected)
    account = account_status()
    if not account['initialized']:
        raise ProtocolError('not_initialized', 'Initialize a Linux account before desktop startup')
    if params.get('require_idle', True) and Path('/run/seatd.sock').exists():
        raise ProtocolError('session_busy', 'A Guest seat owner already exists')
    return dict(compatible=True, guest_interface_abi=1, guest_profile_sha256=contract['guest_profile_sha256'],
                sharing_path=requested, account=account,
                components_verified={name: value.get('version') for name, value in manifests.items()})


def session_status(instance, guest):
    instance = uuid.UUID(instance)
    try:
        guest['read_spec'](instance)
    except FileNotFoundError:
        return dict(instance=str(instance), state='unknown', descriptor_present=False, gpu_retired=False)
    return session_unit_status(instance)


def session_unit_status(instance):
    # The caller already validated identity before logout. Normal cleanup may
    # remove the descriptor; do not require it again after the stop operation.
    spec, _ = profile()
    prefix = {'plasma': 'wsx-cachyos-plasma-', 'hyprland': 'wsx-omarchy-'}[spec['implementation']]
    result = subprocess.run(['/usr/bin/systemctl', 'show', prefix + instance.hex + '.service',
                             '--property=ActiveState,SubState,Result'], check=True,
                            capture_output=True, text=True, timeout=10)
    fields = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
    state = {'active': 'running', 'activating': 'starting', 'deactivating': 'stopping',
             'inactive': 'stopped', 'failed': 'failed'}.get(fields.get('ActiveState'), 'unknown')
    return dict(instance=str(instance), state=state, result=fields.get('Result'), gpu_retired=False)


def session_stop(instance, guest):
    instance = uuid.UUID(instance)
    guest['read_spec'](instance)
    # Reuse the already verified exact-instance normal logout adapter. The
    # native memory/device retirement remains the Host's separate obligation.
    helper = runpy.run_path('/usr/lib/wsx/protocol-retirement.py')
    timing = helper['stop_session'](instance)
    observed = session_unit_status(instance)
    # A unit can retain a failed result after all session processes have
    # drained. Report the failure separately; this never proves GPU retirement.
    if observed['state'] not in ('stopped', 'failed'):
        raise ProtocolError('session_retained', 'Guest session did not stop normally')
    return dict(instance=str(instance), session_retired=True, gpu_retired=False,
                session_result=observed['state'], timing=timing)


def display_snapshot(observed):
    from fractions import Fraction
    monitor = observed['monitor']
    modes = [dict(id=str(i), width=m['width'], height=m['height'],
                  refresh_millihz=round(m['refresh'] * 1000)) for i, m in enumerate(observed['modes'])]
    scale = Fraction(str(monitor['scale'])).limit_denominator(120)
    snapshot = dict(session_generation=observed['signature'],
                outputs=[dict(id=monitor['name'], enabled=True, transform='normal',
                    physical_size=dict(width=monitor['width'], height=monitor['height']),
                    logical_position=dict(x=0,y=0),
                    scale=dict(numerator=scale.numerator,denominator=scale.denominator), modes=modes)],
                limits=dict(max_active_outputs=1, rotation=False, atomic_layout=False,
                    scale=dict(minimum=0.5, maximum=8, integral_logical_dimensions=True),
                    persistence=['backend-default']),
                settings_may_persist=observed.get('compositor') == 'kwin')
    # Hash the public display configuration, excluding compositor telemetry such
    # as focus, active workspace and animation state from the raw monitor object.
    snapshot['generation'] = hashlib.sha256(
        json.dumps(snapshot, sort_keys=True).encode()).hexdigest()
    return snapshot


def display_operation(operation, params):
    adapter = runpy.run_path('/usr/lib/wsx/protocol-display.py')['execute']
    observed = adapter(dict(action='query', instance=params['instance']))
    snapshot = display_snapshot(observed)
    if operation == 'display.query': return snapshot
    if params.get('expected_generation') != snapshot['generation'] or params.get('session_generation') != snapshot['session_generation']:
        raise ProtocolError('stale_generation', 'Display/session changed; query again before applying')
    if params.get('output_id') != snapshot['outputs'][0]['id'] or params.get('transform', 'normal') != 'normal':
        raise ProtocolError('unsupported_configuration', 'This adapter supports one unrotated output')
    if params.get('persistence') != 'backend-default':
        raise ProtocolError('unsupported_persistence', 'This adapter cannot guarantee requested persistence')
    mode = next((m for m in snapshot['outputs'][0]['modes'] if m['id'] == params.get('mode_id')), None)
    if mode is None: raise ProtocolError('unsupported_mode', 'Mode was not advertised')
    ratio = params['scale']
    if type(ratio.get('numerator')) is not int or type(ratio.get('denominator')) is not int or ratio['denominator'] <= 0:
        raise ProtocolError('invalid_request', 'Scale must be a positive rational')
    scale = ratio['numerator'] / ratio['denominator']
    # Alpha uses only the same integral logical dimensions as the verified path.
    if not 0.5 <= scale <= 8 or any((v * ratio['denominator']) % ratio['numerator'] for v in (mode['width'],mode['height'])):
        raise ProtocolError('unsupported_scale', 'Scale is outside this adapter capability')
    chosen = observed['modes'][int(mode['id'])]
    adapter(dict(action='apply', instance=params['instance'], signature=observed['signature'],
                 fit=dict(mode=chosen, guest_scale=scale)))
    after = adapter(dict(action='query', instance=params['instance']))
    if after['signature'] != observed['signature']:
        raise ProtocolError('stale_generation', 'Compositor changed while applying display settings')
    actual = after['monitor']
    if (actual['width'] != mode['width'] or actual['height'] != mode['height'] or
            abs(actual['scale'] - scale) > 0.001):
        raise ProtocolError('apply_not_confirmed', 'Display readback differs from the requested mode/scale')
    result = display_snapshot(after)
    result['applied'] = True
    return result


def dispatch(operation, params, guest):
    if operation == 'capabilities':
        return dict(major=MAJOR, minor=MINOR, capabilities=CAPABILITIES,
                    lifecycle_abi=1, display_abi=1)
    if operation == 'account.status': return account_status()
    if operation == 'desktop.preflight': return preflight(params, guest)
    if operation == 'session.status': return session_status(params['instance'], guest)
    if operation == 'session.stop': return session_stop(params['instance'], guest)
    if operation in ('display.query', 'display.apply'):
        return display_operation(operation, params)
    raise ProtocolError('unsupported_operation', 'Guest operation is not supported')


def handle(request, guest):
    identifier = request.get('id') if isinstance(request, dict) else None
    response = dict(protocol='wsx-guest', major=MAJOR, minor=MINOR, id=identifier)
    try:
        if not isinstance(identifier, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,96}', identifier):
            raise ProtocolError('invalid_request', 'Invalid request identifier')
        if request.get('protocol') != 'wsx-guest' or type(request.get('major')) is not int or request['major'] != MAJOR:
            raise ProtocolError('unsupported_version', 'Unsupported Guest protocol major version')
        if type(request.get('minor')) is not int or not 0 <= request['minor'] <= MINOR:
            raise ProtocolError('unsupported_version', 'Requested minor version is unavailable')
        if not isinstance(request.get('params'), dict) or not isinstance(request.get('operation'), str):
            raise ProtocolError('invalid_request', 'Operation and object parameters are required')
        response.update(ok=True, result=dispatch(request['operation'], request['params'], guest))
    except ProtocolError as error:
        response.update(ok=False, error=dict(code=error.code, message=str(error), retryable=error.retryable))
    except (ValueError, KeyError, TypeError, RuntimeError, OSError, subprocess.SubprocessError) as error:
        response.update(ok=False, error=dict(code='guest_operation_failed', message=str(error)[:2048], retryable=False))
    return response


def record_retirement_reply(request, reply):
    if not isinstance(request, dict) or request.get('operation') != 'session.stop':
        return
    try:
        instance = uuid.UUID(request['params']['instance'])
        directory = Path('/var/lib/wsx/retirement-diagnostics')
        directory.mkdir(parents=True, mode=0o700, exist_ok=True)
        info = directory.lstat()
        if directory.is_symlink() or info.st_uid != 0 or info.st_mode & 0o077:
            raise ValueError('Unsafe retirement diagnostics directory')
        # Fixed per-instance snapshot; atomic, bounded, no credentials/request body.
        target = directory / ('session-stop-' + instance.hex + '.json')
        temporary = directory / ('.retirement-' + uuid.uuid4().hex)
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            with os.fdopen(fd, 'w') as stream:
                json.dump(reply, stream, ensure_ascii=True)
                stream.flush(); os.fsync(stream.fileno())
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print('Retirement diagnostic write failed: ' + str(error), file=sys.stderr)


def serve(guest):
    # One bounded request per invocation; no service, daemon or reusable handles.
    try:
        raw = sys.stdin.buffer.read(LIMIT + 1)
        if len(raw) > LIMIT: raise ValueError('Request exceeds 1 MiB')
        request = json.loads(raw)
        with contextlib.redirect_stdout(sys.stderr):
            reply = handle(request, guest)
            record_retirement_reply(request, reply)
    except (ValueError, UnicodeError) as error:
        reply = dict(protocol='wsx-guest', major=MAJOR, minor=MINOR, id=None, ok=False,
                     error=dict(code='invalid_request', message=str(error), retryable=False))
    encoded = json.dumps(reply, ensure_ascii=True)
    if len(encoded) > LIMIT:
        encoded = json.dumps(dict(protocol='wsx-guest', major=MAJOR, minor=MINOR, id=reply.get('id'), ok=False,
                                 error=dict(code='response_too_large', message='Reply exceeds 1 MiB', retryable=False)))
    print(encoded)
