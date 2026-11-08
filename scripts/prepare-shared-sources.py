#!/usr/bin/env python3
"""Prepare source-only shared assets from existing private components; never compile."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time

import component_registry as registry
from component_materials import sha
from shared_sources import ROOT, REPOSITORY, INDEX, ARCHIVES, make_bundle, verify_bundle, download_index


def gh(*args):
    return subprocess.check_output(['gh', *map(str,args)], text=True)


def api(path):
    if path.startswith('repos/WSLd-wsx/wsx-rootfs-ops/'):
        token = os.environ.get('WSX_OPS_TOKEN')
        if not token:
            raise ValueError('Operations run access requires WSX_OPS_TOKEN')
        return json.loads(subprocess.check_output(['gh', 'api', path], text=True,
                                                  env=dict(os.environ, GH_TOKEN=token)))
    return json.loads(gh('api',path))


def load_script(name):
    spec = importlib.util.spec_from_file_location(name.replace('-','_'), ROOT/'scripts'/name)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def releases():
    pages = json.loads(gh('api', '--paginate', '--slurp', f'repos/{REPOSITORY}/releases?per_page=100'))
    if not isinstance(pages, list) or any(not isinstance(page, list) for page in pages):
        raise ValueError('Invalid release listing')
    return [release for page in pages for release in page]


def find_release(tag, attempts=10):
    # GitHub's tag endpoint does not resolve unpublished Drafts reliably.
    # Discover the authenticated Draft through the list, then use its stable ID.
    for attempt in range(attempts):
        matches=[r for r in releases() if r['tag_name']==tag]
        if len(matches)>1:
            raise ValueError('Duplicate shared source release')
        if matches:
            return api(f'repos/{REPOSITORY}/releases/{matches[0]["id"]}')
        if attempt+1<attempts:
            time.sleep(2)
    raise ValueError('Shared source Draft not visible yet; retry with the same inputs')


def acquire(profile, directory, pin=None):
    if pin is None:
        config = json.loads((ROOT/'components/source-delivery.json').read_text())
        pin = config['component_origins'][profile]
    if not isinstance(pin, dict):
        raise ValueError('A verified component origin is required')
    reuse = load_script('reuse-components.py')
    run_repo = pin.get('run_repository', REPOSITORY)
    if run_repo not in (REPOSITORY, 'WSLd-wsx/wsx-rootfs-ops'):
        raise ValueError('Unapproved component workflow repository')
    run = api(f'repos/{run_repo}/actions/runs/{pin["run_id"]}')
    reuse.validate_origin(pin,profile,REPOSITORY,run,{})
    package = directory/'package'; package.mkdir()
    with registry.docker_session() as env:
        registry.fetch(pin['image'],package,pin,profile,env)
    if sha(package/'manifest.json') != pin['manifest_sha256']:
        raise ValueError('Original component manifest differs from approved pin')
    manifest = json.loads((package/'manifest.json').read_text())
    admitted = directory/'admitted'
    load_script('consume-source-components.py').consume(package,admitted,profile,manifest['sha256'])
    return admitted


def publish_draft(bundle):
    index = verify_bundle(bundle)
    tag = index['tag']
    matches = [r for r in releases() if r['tag_name']==tag]
    if len(matches)>1:
        raise ValueError('Duplicate shared source release')
    if not matches:
        notes = ('Shared graphics source materials only; contains no rootfs or graphics binaries.\n\n'
                 'Notices, fixed origins and changes are separate from retained upstream source archives.\n'
                 'The original private component package is unchanged.\n'
                 'Do not use a Draft URL as public source delivery; publication and pin activation are separate.\n')
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'notes.txt';path.write_text(notes)
            gh('release','create',tag,'--repo',REPOSITORY,'--draft','--target',subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
               '--title','Shared graphics sources: '+index['profile'],'--notes-file',path)
    release = find_release(tag)
    assets = {a['name']:a for a in release['assets']}
    if len(assets) != len(release['assets']):
        raise ValueError('Duplicate shared source release assets')
    names = list(ARCHIVES)+[INDEX]
    if set(assets)-set(names):
        raise ValueError('Unexpected shared source release assets')
    # Preflight all existing assets before uploading; never overwrite public bytes.
    for name,asset in assets.items():
        expected=sha(bundle/name)
        if asset['size']!=(bundle/name).stat().st_size or asset.get('digest')!='sha256:'+expected:
            raise ValueError('Existing shared source asset differs: '+name)
    if not release['draft'] and set(assets)!=set(names):
        raise ValueError('Incomplete public shared source release; do not mutate')
    for name in names:
        if name not in assets:
            gh('release','upload',tag,bundle/name,'--repo',REPOSITORY)
    release=api(f'repos/{REPOSITORY}/releases/{release["id"]}')
    assets={a['name']:a for a in release['assets']}
    if len(assets)!=len(release['assets']) or set(assets)!=set(names):
        raise ValueError('Incomplete shared source upload')
    # Read back every source-only asset, without changing release visibility.
    with tempfile.TemporaryDirectory() as temporary:
        for name in names:
            path=Path(temporary)/name
            with path.open('wb') as stream:
                subprocess.run(['gh','api','-H','Accept: application/octet-stream',
                    f'repos/{REPOSITORY}/releases/assets/{assets[name]["id"]}'],stdout=stream,check=True)
            if sha(path)!=sha(bundle/name):
                raise ValueError('Shared source read-back mismatch: '+name)
    return dict(tag=tag,manifest_sha256=sha(bundle/INDEX),draft=release['draft'],
                release_id=release['id'],url=release['html_url'])


def publish_public(bundle):
    """Publish a fully read-back source-only Draft and verify anonymous access."""
    index = verify_bundle(bundle)
    repo = api('repos/' + REPOSITORY)
    if repo.get('full_name') != REPOSITORY or repo.get('private') is not False:
        raise ValueError('Public source publication requires the approved public repository')
    result = publish_draft(bundle)
    if result['tag'] != index['tag'] or result['manifest_sha256'] != sha(bundle/INDEX):
        raise ValueError('Published source identity differs from verified bundle')
    if result['draft']:
        gh('release', 'edit', result['tag'], '--repo', REPOSITORY,
           '--draft=false', '--prerelease', '--latest=false')
    pin = dict(tag=result['tag'], manifest_sha256=result['manifest_sha256'])
    if download_index(pin, index['profile']) != (bundle/INDEX).read_bytes():
        raise ValueError('Public source index differs from verified bundle')
    return pin


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile',choices=('omarchy','cachyos-plasma'),required=True)
    parser.add_argument('--work',type=Path,required=True)
    parser.add_argument('--component-pin',type=Path,
                        help='Explicit component origin JSON; all origin and package checks still apply')
    parser.add_argument('--require-current-compatibility',action='store_true',
                        help='Reject components whose compiled inputs differ from the current recipe')
    publication=parser.add_mutually_exclusive_group()
    publication.add_argument('--publish-draft',action='store_true')
    publication.add_argument('--publish-public',action='store_true',
                             help='Publish the verified source-only bundle as a public prerelease')
    args=parser.parse_args()
    args.work.mkdir(parents=True,exist_ok=False)
    pin=json.loads(args.component_pin.read_text()) if args.component_pin else None
    admitted=acquire(args.profile,args.work,pin)
    if args.require_current_compatibility:
        load_script('reuse-components.py').check_compatibility(ROOT,admitted)
    bundle=args.work/'shared-sources'
    index=make_bundle(admitted,bundle)
    result=dict(profile=args.profile,tag=index['tag'],manifest_sha256=sha(bundle/INDEX),
                original_size=(index['original_sources']['size'] if index.get('original_sources') else None),
                shared_files=[{k:f[k] for k in ('name','size','sha256')} for f in index['files']],
                index_size=(bundle/INDEX).stat().st_size,
                compiled=False,private_component_changed=False)
    (args.work/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    if args.publish_draft:
        result['release']=publish_draft(bundle)
    elif args.publish_public:
        result['public_source']=publish_public(bundle)
    (args.work/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print('SHARED_SOURCE_RESULT '+json.dumps(result,separators=(',',':')))
