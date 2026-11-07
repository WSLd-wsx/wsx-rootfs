"""Transport paired component files through private, digest-pinned GHCR images."""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from urllib.parse import quote

REPOSITORY = 'WSLd-wsx/wsx-rootfs'
IMAGE = 'ghcr.io/wsld-wsx/wsx-rootfs/graphics-components'
OPS_IMAGE = 'ghcr.io/wsld-wsx/wsx-rootfs-ops/graphics-components'


def check_reference(reference):
    if not any(re.fullmatch(re.escape(image) + r'@sha256:[0-9a-f]{64}', reference)
               for image in (IMAGE, OPS_IMAGE)):
        raise ValueError('Expected an immutable component digest in the approved registry namespace')


def require_private(image=IMAGE, allow_missing=False):
    repo = json.loads(subprocess.check_output(['gh', 'api', 'repos/' + REPOSITORY]))
    if repo.get('full_name') != REPOSITORY or type(repo.get('private')) is not bool:
        raise ValueError('Approved repository identity and visibility required')
    if image not in (IMAGE, OPS_IMAGE):
        raise ValueError('Unapproved component package')
    name = image.removeprefix('ghcr.io/wsld-wsx/')
    env = dict(os.environ)
    if env.get('WSX_COMPONENT_REGISTRY_TOKEN'):
        env['GH_TOKEN'] = env['WSX_COMPONENT_REGISTRY_TOKEN']
    result = subprocess.run(['gh', 'api', '--include',
        'orgs/WSLd-wsx/packages/container/' + quote(name, safe='')], capture_output=True, text=True, env=env)
    if result.returncode:
        if allow_missing and repo['private'] and re.search(r'^HTTP/\S+ 404\b', result.stdout, re.M):
            return
        raise ValueError('Cannot verify private registry package access')
    document = json.loads(result.stdout.split('\r\n\r\n' if '\r\n\r\n' in result.stdout else '\n\n', 1)[1])
    if document.get('visibility') != 'private':
        raise ValueError('Registry package must remain private')


@contextmanager
def docker_session():
    with tempfile.TemporaryDirectory(prefix='wsx-registry-auth-') as config:
        env = dict(os.environ, DOCKER_CONFIG=config)
        token = env.get('WSX_COMPONENT_REGISTRY_TOKEN') or env.get('GH_TOKEN')
        if not token:
            raise ValueError('GH_TOKEN required for private registry access')
        actor = env.get('GITHUB_ACTOR') or json.loads(subprocess.check_output(['gh', 'api', 'user']))['login']
        subprocess.run(['docker', 'login', 'ghcr.io', '-u', actor, '--password-stdin'],
                       input=token, text=True, env=env, stdout=subprocess.DEVNULL, check=True)
        yield env


def validate_labels(labels, pin, profile):
    expected = {'org.opencontainers.image.source': 'https://github.com/' + REPOSITORY,
                'org.opencontainers.image.revision': pin['source_commit'],
                'io.wsx.run-id': str(pin['run_id']), 'io.wsx.profile': profile}
    if any(labels.get(key) != value for key, value in expected.items()):
        raise ValueError('Registry image build origin mismatch')


def fetch(reference, destination, pin, profile, env):
    check_reference(reference)
    subprocess.run(['docker', 'pull', reference], env=env, check=True)
    info = json.loads(subprocess.check_output(['docker', 'image', 'inspect', reference], env=env))[0]
    validate_labels(info['Config'].get('Labels') or {}, pin, profile)
    container = subprocess.check_output(['docker', 'create', reference], env=env, text=True).strip()
    try:
        subprocess.run(['docker', 'cp', container + ':/payload/.', str(destination)], env=env, check=True)
    finally:
        subprocess.run(['docker', 'rm', container], env=env, check=True, stdout=subprocess.DEVNULL)


def publication_origin(environ):
    selected = environ.get('WSX_COMPONENT_IMAGE', IMAGE)
    if selected not in (IMAGE, OPS_IMAGE):
        raise ValueError('Unapproved component destination')
    run_repo = environ.get('GITHUB_REPOSITORY', REPOSITORY)
    if run_repo == 'WSLd-wsx/wsx-rootfs-ops':
        if selected != OPS_IMAGE:
            raise ValueError('Operations builds must target the private operations package')
        commit = environ.get('WSX_SOURCE_COMMIT', '')
        operations_commit = environ.get('GITHUB_SHA', '')
        if not re.fullmatch('[0-9a-f]{40}', commit) or not re.fullmatch('[0-9a-f]{40}', operations_commit):
            raise ValueError('Exact source and operations commits are required')
    elif run_repo == REPOSITORY and selected == IMAGE:
        commit = environ.get('GITHUB_SHA', '')
        operations_commit = None
        if not re.fullmatch('[0-9a-f]{40}', commit):
            raise ValueError('Exact source commit required')
    else:
        raise ValueError('Unapproved component build repository')
    return selected, run_repo, commit, operations_commit


def publish(bundle, profile, probe=False):
    if probe:
        raise ValueError('Component package publication does not support probe destinations')
    image, run_repo, commit, operations_commit = publication_origin(os.environ)
    require_private(image, allow_missing=True)
    run = int(os.environ['GITHUB_RUN_ID'])
    attempt = int(os.environ.get('GITHUB_RUN_ATTEMPT', '1'))
    tag = f'{image}:{profile}-{commit}-{run}-{attempt}'
    files = sorted(bundle.iterdir())
    if not files or any(not p.is_file() or p.is_symlink() for p in files):
        raise ValueError('Expected a flat package of regular files')
    labels = {'org.opencontainers.image.source': 'https://github.com/' + REPOSITORY,
              'org.opencontainers.image.revision': commit,
              'io.wsx.run-id': str(run), 'io.wsx.profile': profile}
    dockerfile = 'FROM scratch\nCOPY . /payload/\nCMD ["/not-executable"]\n'
    with docker_session() as env:
        command = ['docker', 'build', '-t', tag, '-f', '-']
        for key, value in labels.items():
            command += ['--label', key + '=' + value]
        subprocess.run(command + [str(bundle)], input=dockerfile, text=True, env=env, check=True)
        subprocess.run(['docker', 'push', tag], env=env, check=True)
        require_private(image)
        info = json.loads(subprocess.check_output(['docker', 'image', 'inspect', tag], env=env))[0]
        references = [r for r in info.get('RepoDigests', []) if r.startswith(image + '@sha256:')]
        if len(references) != 1:
            raise ValueError('No unique pushed digest')
        reference = references[0]
        # Read back every delivered byte through the registry, not the build tag.
        subprocess.run(['docker', 'pull', reference], env=env, check=True)
        container = subprocess.check_output(['docker', 'create', reference], env=env, text=True).strip()
        try:
            with tempfile.TemporaryDirectory(prefix='wsx-registry-check-') as temporary:
                subprocess.run(['docker', 'cp', container + ':/payload/.', temporary], env=env, check=True)
                def hashes(directory):
                    result = {}
                    for path in Path(directory).iterdir():
                        if path.is_symlink() or not path.is_file():
                            raise ValueError('Unexpected registry payload member')
                        with path.open('rb') as stream:
                            result[path.name] = hashlib.file_digest(stream, 'sha256').hexdigest()
                    return result
                if hashes(temporary) != hashes(bundle):
                    raise ValueError('Registry read-back differs from published package')
        finally:
            subprocess.run(['docker', 'rm', container], env=env, check=True, stdout=subprocess.DEVNULL)
    pin = dict(transport='ghcr', image=reference, run_id=run, source_commit=commit,
               manifest_sha256=hashlib.sha256((bundle/'manifest.json').read_bytes()).hexdigest())
    if operations_commit:
        pin.update(run_repository=run_repo, workflow_commit=operations_commit)
    return pin


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', type=Path)
    parser.add_argument('--profile', required=True, choices=('omarchy', 'cachyos-plasma'))
    parser.add_argument('--probe', action='store_true')
    args = parser.parse_args()
    pin = publish(args.bundle, args.profile, args.probe)
    text = '```json\n' + json.dumps(pin, indent=2) + '\n```\n'
    print(text)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as stream:
            stream.write(('Probe only; do not select this package.\n' if args.probe else
                          'Select this verified package explicitly in components/reuse.json.\n') + text)
