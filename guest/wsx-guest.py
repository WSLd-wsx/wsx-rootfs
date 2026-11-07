#!/usr/bin/python3
"""WSX Guest lifecycle ABI 1. Root-only control; no GPU/module bootstrap."""
import argparse
import configparser
import getpass
import fcntl
import json
import os
from pathlib import Path
import pwd
import runpy
import re
import subprocess
import sys
import uuid

STATE = Path('/var/lib/wsx/initialized.json')
RUNTIME = Path('/usr/lib/wsx/runtime')


def run(argv, **kwargs):
    return subprocess.run(argv, check=True, **kwargs)


def spec_path(instance):
    return Path('/run/wsx')/(instance.hex+'.json')


def read_spec(instance):
    path = spec_path(instance)
    status = path.lstat()
    if path.is_symlink() or status.st_uid != 0 or status.st_mode & 0o077:
        raise ValueError('Unsafe runtime descriptor permissions')
    spec = json.loads(path.read_text())
    if spec['instance_id'] != str(instance):
        raise ValueError('Instance identity mismatch')
    return spec


def initialize(args):
    if STATE.exists():
        raise ValueError('Guest already initialized; use normal account tools for later changes')
    if not re.fullmatch(r'[a-z_][a-z0-9_-]{0,30}', args.user) or args.user == 'root':
        raise ValueError('Invalid non-root username')
    pending_path = STATE.with_name('initialization-pending.json')
    expected = dict(user=args.user, locale=args.locale, timezone=args.timezone)
    pending = json.loads(pending_path.read_text()) if pending_path.exists() else {}
    if pending and any(pending.get(k) != v for k, v in expected.items()):
        raise ValueError('Different initialization is pending; inspect it before continuing')
    try:
        existing = pwd.getpwnam(args.user)
    except KeyError:
        existing = None
    if existing is not None and pending.get('created_uid') != existing.pw_uid:
        raise ValueError('Existing user is not owned by this initialization')
    zone = (Path('/usr/share/zoneinfo')/args.timezone).resolve(strict=True)
    if not zone.is_relative_to('/usr/share/zoneinfo') or not zone.is_file():
        raise ValueError('Invalid timezone')
    if args.locale != 'C.UTF-8':
        if not re.fullmatch(r'[a-z]{2,3}_[A-Z]{2}\.UTF-8',args.locale) or not (Path('/usr/share/i18n/locales')/args.locale.split('.')[0]).is_file():
            raise ValueError('Locale is not provided by the installed locale data')
    if args.password_stdin:
        password = sys.stdin.readline().removesuffix('\n')
    else:
        password = getpass.getpass('New user password: ')
        if password != getpass.getpass('Confirm password: '):
            raise ValueError('Passwords differ')
    if not password or any(c in password for c in '\r\n\0'):
        raise ValueError('A nonempty single-line password is required')
    if args.locale != 'C.UTF-8':
        run(['localedef','-i',args.locale.split('.')[0],'-f','UTF-8',args.locale])
    if not pending:
        pending_path.write_text(json.dumps(expected)+'\n')
        pending_path.chmod(0o600)
    if existing is None:
        run(['useradd','--create-home','--groups','wheel,audio,video,render','--shell','/bin/bash',args.user])
        expected['created_uid'] = pwd.getpwnam(args.user).pw_uid
        pending_path.write_text(json.dumps(expected)+'\n')
    # The secret is stdin to chpasswd, never argv, logs, environment or manifests.
    run(['chpasswd'], input=args.user+':'+password+'\n', text=True)
    del password
    Path('/etc/localtime').unlink(missing_ok=True)
    Path('/etc/localtime').symlink_to(zone)
    Path('/etc/locale.conf').write_text('LANG='+args.locale+'\n')
    account = pwd.getpwnam(args.user)
    env = dict(PATH='/usr/share/omarchy/bin:/usr/bin', HOME=account.pw_dir,
               USER=args.user, LOGNAME=args.user, OMARCHY_PATH='/usr/share/omarchy',
               OMARCHY_SETUP_CONTEXT='iso-chroot', WSX_WSL_NETWORK='1', LANG=args.locale)
    # Seed only per-user theme/configuration leaves, not hardware/boot migration.
    run(['runuser','-u',args.user,'--','env',*[k+'='+v for k,v in env.items()],
         'bash','-eu','/usr/lib/wsx/initialize-user.sh'])
    STATE.parent.mkdir(parents=True,exist_ok=True)
    pending=STATE.with_suffix('.new')
    pending.write_text(json.dumps(dict(guest_interface_abi=1,user=args.user,locale=args.locale,timezone=args.timezone))+'\n')
    pending.chmod(0o600)
    configuration=configparser.ConfigParser()
    configuration.read('/etc/wsl.conf')
    configuration['user']={'default':args.user}
    with Path('/etc/wsl.conf').open('w') as stream:
        configuration.write(stream)
    pending.replace(STATE)
    pending_path.unlink()


def prepare(args):
    initialized = json.loads(STATE.read_text())
    spec=json.load(sys.stdin)
    if type(spec.get('guest_interface_abi')) is not int or spec['guest_interface_abi'] != 1:
        raise ValueError('Unsupported Guest interface ABI')
    instance=uuid.UUID(spec['instance_id'])
    if not instance.int or spec.get('sharing_path') not in ('linear-v1','opaque-v1'):
        raise ValueError('Missing instance or negotiated sharing path')
    node=spec['drm_node']
    if not re.fullmatch(r'/dev/dri/card[0-9]+',node):
        raise ValueError('Expected actual DRM card')
    if type(spec['input_port']) is not int or not 1 <= spec['input_port'] < 2**32:
        raise ValueError('Invalid vsock port')
    pulse = spec.get('pulse_server')
    if pulse is not None:
        if not isinstance(pulse,str) or not pulse.startswith('unix:') or not Path(pulse[5:]).is_socket():
            raise ValueError('Audio endpoint must be an existing explicitly supplied Unix socket')
    # Follow the same VMBus identity discovery used by the prototype owner.
    card=Path('/sys/class/drm')/Path(node).name
    found=False
    for parent in card.resolve(strict=True).parents:
        subsystem=parent/'subsystem'
        if subsystem.is_symlink() and subsystem.resolve().name=='vmbus':
            found=uuid.UUID((parent/'device_id').read_text().strip().strip('{}'))==instance
            break
    if not found:
        raise ValueError('DRM node does not belong to the supplied host instance')
    for name in ('mesa/manifest.json','venus/manifest.json','opaque-consumer/manifest.json','wsx-input-guest'):
        if not (RUNTIME/name).is_file():
            raise ValueError('Incomplete private runtime: '+name)
    view=runpy.run_path('/usr/lib/wsx/device-view.py')['prepare'](instance,node)
    print('WSX_DEVICE_VIEW '+json.dumps(view),file=sys.stderr,flush=True)
    if not Path(node).is_char_device():
        raise ValueError('Selected DRM node is unavailable in the device view')
    spec['user']=initialized['user']; spec['locale']=initialized['locale']; spec['port']=spec['input_port']-1
    directory=Path('/run/wsx'); directory.mkdir(mode=0o700,exist_ok=True)
    target=spec_path(instance)
    # Exclusive create prevents replacement of a retained owner/session spec.
    fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'w') as stream:
        json.dump(spec,stream)
    print(json.dumps({'prepared':True,'instance_id':str(instance),'gpu_started':False}))


def main():
    if os.geteuid()!=0:
        raise SystemExit('Root control channel required')
    if sys.argv[1:] == ['host-call']:
        return runpy.run_path('/usr/lib/wsx/guest-protocol.py')['serve'](globals())
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest='command',required=True)
    init=sub.add_parser('initialize'); init.add_argument('--user',required=True)
    init.add_argument('--locale',default='en_US.UTF-8'); init.add_argument('--timezone',required=True)
    init.add_argument('--password-stdin',action='store_true')
    sub.add_parser('prepare')
    for name in ('start','status','stop','diagnostics','session'):
        sub.add_parser(name).add_argument('--instance',required=True,type=uuid.UUID)
    args=p.parse_args()
    if args.command=='initialize':
        os.umask(0o077)
        STATE.parent.mkdir(parents=True,exist_ok=True)
        with (STATE.parent/'initialization.lock').open('a') as lock:
            fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
            return initialize(args)
    if args.command=='prepare': return prepare(args)
    spec=read_spec(args.instance)
    unit='wsx-omarchy-'+args.instance.hex+'.service'
    if args.command=='start':
        run(['systemd-run','--wait','--unit='+unit,'--property=Type=exec',
             '--property=KillMode=control-group','--property=TimeoutStopSec=30',
             '/usr/bin/wsx-guest','session','--instance',str(args.instance)])
    elif args.command=='session':
        env=dict(os.environ,WSX_USER=spec['user'],WSX_SHARING_PATH=spec['sharing_path'],WSX_LOCALE=spec['locale'])
        os.execve('/usr/bin/python3',['python3','-I',str(RUNTIME/'desktop.py'),
                  spec['drm_node'],str(args.instance)],env)
    elif args.command=='status':
        run(['systemctl','show',unit,'--property=ActiveState,SubState,Result,ExecMainStatus'])
    elif args.command=='stop':
        # Normal session shutdown only. Native ownership retirement is core's job.
        run(['systemctl','stop',unit])
    else:
        run(['journalctl','--no-pager','-u',unit,'-n','200'])


if __name__=='__main__':
    main()
