# SPDX-License-Identifier: GPL-2.0-or-later
"""Keep immutable component evidence separate from current image assembly inputs."""
import json
from pathlib import Path
import shutil
import subprocess
from product_licenses import config, classify, check_boundaries, sha, write_component_map
from license_inputs import paths as license_paths

IMAGE_POLICY_FILES = {'LICENSE-MAP.md','docs/licensing/modules.json','components/license-boundaries.json'}


def check_component_inputs(root, work, collection_only_change):
    receipt = json.loads((work/'component-source.json').read_text())
    original = work/'component-materials/notices'
    mapping = json.loads((original/'MODULE-LICENSES.json').read_text())
    modules, rules, boundaries = config(root)
    if (mapping['module_definitions'] != modules['modules'] or
            mapping['license_selection'] != modules['license_selection'] or
            mapping['license_grant'] != modules['license_grant']):
        raise ValueError('Compiled component license terms changed')
    # Appending scoped image notices is allowed; existing text cannot be rewritten.
    if not (root/'LICENSE-MAP.md').read_bytes().startswith((original/'LICENSE-MAP.md').read_bytes()):
        raise ValueError('Existing component license map text changed')
    for name in license_paths(root):
        if mapping['policy_files'].get(name) != receipt['recipe_files'].get(name):
            raise ValueError('Original component policy receipt mismatch: '+name)
        if name not in IMAGE_POLICY_FILES and receipt['recipe_files'].get(name) != sha(root/name):
            raise ValueError('Compiled component license policy changed: '+name)
    current = check_boundaries(root)['paired-component-build']
    recorded = mapping['reconstruction_closures']['paired-component-build']
    if current != recorded:
        raise ValueError('Component reconstruction dependency graph changed')
    ids = {entry['output'] for entry in mapping['component_runtime_files']}
    if not ids or {r['component_path']:r['sha256'] for r in mapping['component_runtime_files']} != receipt['runtime_files']:
        raise ValueError('Compiled runtime mapping differs from original receipt')
    outputs = {entry['id']:entry for entry in boundaries['outputs']}
    required = set(current['files']) | {'components/sources.json','components/builder.json'}
    compiled = set()
    for original_output in mapping['outputs']:
        if original_output['id'] not in ids: continue
        expected = {k:v for k,v in original_output.items() if k != 'inventoried_sources'}
        if outputs.get(original_output['id']) != expected:
            raise ValueError('Compiled output boundary changed: '+original_output['id'])
        compiled.update(original_output['inventoried_sources'])
    required.update(compiled)
    for name in sorted(required):
        path = root/name
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError('Missing or unsafe component input: '+name)
        if name not in IMAGE_POLICY_FILES and receipt['recipe_files'].get(name) != sha(path):
            if name not in compiled and collection_only_change(root,name,receipt['recipe_files'].get(name)):
                continue
            raise ValueError('Pinned component/source boundary differs: '+name+'; select a matching package')
        observed = mapping['source_files'][name]
        if classify(name,modules,rules) != {k:v for k,v in observed.items() if k != 'sha256'}:
            raise ValueError('Compiled input license classification changed: '+name)


def image_snapshot(root, work):
    """A source snapshot, explicitly not a fabricated component compilation receipt."""
    original = json.loads((work/'component-source.json').read_text())
    names = subprocess.check_output(['git','ls-files','-co','--exclude-standard','-z'],cwd=root).decode().split('\0')
    files = {}
    for name in sorted(set(filter(None,names))):
        p=root/name
        if p.is_symlink() or not p.is_file() or not p.resolve().is_relative_to(root.resolve()):
            raise ValueError('Unsafe image source snapshot input: '+name)
        files[name]=sha(p)
    snapshot = dict(schema_version=1, origin='image-assembly-source-snapshot',compiled=False,
        profile=original['profile'], component_source_sha256=sha(work/'component-source.json'),
        recipe_files=files, runtime_files=original['runtime_files'])
    destination=work/'image-materials'
    destination.mkdir(exist_ok=False)
    notices=destination/'component-materials/notices'
    shutil.copytree(work/'component-materials/notices',notices)
    # Derive new image notices, retaining the immutable originals separately.
    write_component_map(root,snapshot,notices)
    (destination/'image-source.json').write_text(json.dumps(snapshot,indent=2)+'\n')
    return snapshot


def verify_image_snapshot(root,work):
    path=work/'image-materials/image-source.json'
    snapshot=json.loads(path.read_text())
    original=json.loads((work/'component-source.json').read_text())
    if (snapshot.get('origin') != 'image-assembly-source-snapshot' or snapshot.get('compiled') is not False
            or snapshot['component_source_sha256'] != sha(work/'component-source.json')
            or snapshot['profile'] != original['profile'] or snapshot['runtime_files'] != original['runtime_files']):
        raise ValueError('Image assembly snapshot differs from original component evidence')
    for name,digest in snapshot['recipe_files'].items():
        path=root/name
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()) or not path.is_file() or sha(path)!=digest:
            raise ValueError('Image source changed after snapshot: '+name)
    return snapshot
