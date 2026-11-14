"""Bind module review boundaries to build inputs and actual product files."""
import ast
import fnmatch
import hashlib
import json
from pathlib import Path
from license_inputs import paths as license_paths


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def config(root):
    modules = json.loads((root/'docs/licensing/modules.json').read_text())
    rules = json.loads((root/'docs/licensing/rules.json').read_text())['rules']
    boundaries = json.loads((root/'components/license-boundaries.json').read_text())
    if modules['license_grant'] != boundaries['license_grant']:
        raise ValueError('Inconsistent module grant state')
    if modules['license_grant'] and not modules.get('activation', {}).get('approved_by'):
        raise ValueError('Active grants require an explicit owner approval record')
    return modules, rules, boundaries


def classify(name, modules, rules):
    matches = [r for r in rules if any(fnmatch.fnmatchcase(name, p) for p in r['paths'])]
    if not matches:
        raise ValueError('Unmapped product source: ' + name)
    priority = max(r['priority'] for r in matches)
    selected = [r for r in matches if r['priority'] == priority]
    if len(selected) != 1:
        raise ValueError('Ambiguous product source: ' + name)
    rule = selected[0]
    module = modules['path_overrides'].get(name, modules['rule_modules'].get(rule['id']))
    if module not in modules['modules']:
        raise ValueError('Missing product module: ' + name)
    return dict(module=module, existing_rule=rule['id'], review_group=rule['group'],
                license=modules['modules'][module].get('license'),
                contribution_license=modules.get('expression_exceptions', {}).get(name, {}).get(
                    'owner_contribution_license', modules['modules'][module].get('contribution_license')),
                treatment=modules['modules'][module]['treatment'],
                license_grant=bool(modules['license_grant'] and modules['modules'][module].get('new_grant')))


def local_imports(root, name):
    if not name.endswith('.py'):
        return []
    result = set()
    for node in ast.walk(ast.parse((root/name).read_text())):
        imported = ([n.name for n in node.names] if isinstance(node, ast.Import)
                    else [node.module] if isinstance(node, ast.ImportFrom) and node.module else [])
        for item in imported:
            candidate = Path(name).parent/(item.split('.')[0]+'.py')
            if (root/candidate).is_file():
                result.add(str(candidate))
    return sorted(result)


def dependency_closures(root, boundaries):
    result = {}
    for group, seeds in boundaries['roots'].items():
        seen = set(); pending = list(seeds); edges = []
        while pending:
            name = pending.pop()
            if name in seen:
                continue
            path = root/name
            if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()) or not path.is_file():
                raise ValueError('Missing regular build dependency: ' + name)
            seen.add(name)
            dependencies = sorted(set(boundaries['dependencies'].get(name, []) + local_imports(root, name)))
            edges.extend(dict(source=name, dependency=d) for d in dependencies)
            pending.extend(dependencies)
        result[group] = dict(files=sorted(seen), edges=edges)
    return result


def check_boundaries(root):
    modules, rules, boundaries = config(root)
    closures = dependency_closures(root, boundaries)
    for group, closure in closures.items():
        for name in closure['files']:
            treatment = classify(name, modules, rules)
            if treatment['module'] == 'wsx-independent':
                raise ValueError('PolyForm scope in reconstruction dependency graph: ' + group + ': ' + name)
    return closures


def write_component_map(root, receipt, notices):
    modules, rules, boundaries = config(root)
    for name in license_paths(root):
        if receipt['recipe_files'].get(name) != sha(root/name):
            raise ValueError('License policy missing or changed since compilation: ' + name)
    closures = check_boundaries(root)
    required = set()
    for closure in closures.values():
        required.update(closure['files'])
    for names in boundaries['installed_inputs'].values():
        required.update(names)
    for name in sorted(required):
        path = root/name
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()) or not path.is_file():
            raise ValueError('Unsafe or missing required source: ' + name)
        if receipt['recipe_files'].get(name) != sha(path):
            raise ValueError('Required source absent or changed in compilation receipt: ' + name)
    records = {name: dict(sha256=digest, **classify(name, modules, rules))
               for name, digest in sorted(receipt['recipe_files'].items())}
    outputs = []
    for entry in boundaries['outputs']:
        if receipt.get('profile', 'omarchy') not in entry['profiles']:
            continue
        sources = set()
        for pattern in entry['source_paths']:
            if Path(pattern).is_absolute() or '..' in Path(pattern).parts:
                raise ValueError('Unsafe output source pattern: ' + pattern)
            matches = []
            for candidate in root.glob(pattern):
                if candidate.is_dir() and not candidate.is_symlink():
                    matches.extend(p for p in candidate.rglob('*')
                                   if '__pycache__' not in p.parts and (p.is_file() or p.is_symlink()))
                elif candidate.is_file() or candidate.is_symlink():
                    matches.append(candidate)
            if not matches:
                raise ValueError('Output source pattern matches no files: ' + pattern)
            for path in matches:
                name = str(path.relative_to(root))
                if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
                    raise ValueError('Unsafe output source: ' + name)
                if receipt['recipe_files'].get(name) != sha(path):
                    raise ValueError('Output source absent or changed in compilation receipt: ' + name)
                sources.add(name)
        sources = sorted(sources)
        if not sources:
            raise ValueError('Output lacks inventoried sources: ' + entry['id'])
        outputs.append(dict(entry, inventoried_sources=sources))
    runtime = []
    for name, digest in sorted(receipt.get('runtime_files', {}).items()):
        installed = 'usr/lib/wsx/runtime/'+name
        matches = [o['id'] for o in outputs if any(fnmatch.fnmatchcase(installed, p) for p in o['installed_paths'])]
        if len(matches) != 1:
            raise ValueError('Unmapped/ambiguous compiled output: ' + name)
        runtime.append(dict(component_path=name, sha256=digest, output=matches[0]))
    report = dict(schema_version=1, profile=receipt.get('profile', 'omarchy'),
                  license_grant=modules['license_grant'], release_ready=False,
                  private_artifacts_allowed=modules.get('private_artifacts_allowed',False),
                  policy_files={name: sha(root/name) for name in license_paths(root)},
                  module_definitions=modules['modules'], license_selection=modules['license_selection'],
                  source_files=records, reconstruction_closures=closures,
                  installed_inputs=boundaries['installed_inputs'], outputs=outputs,
                  component_runtime_files=runtime, blockers=boundaries['activation_blockers'])
    (notices/'MODULE-LICENSES.json').write_text(json.dumps(report, indent=2)+'\n')
    (notices/'MODULE-NOTICES.txt').write_text(
        ('MODULE LICENSE APPLICATION — EFFECTIVE OWNER GRANTS\n' if modules['license_grant']
         else 'MODULE LICENSE APPLICATION — INACTIVE TEST FIXTURE\n') +
        'See LICENSE, LICENSE-MAP.md and MODULE-LICENSES.json for exact scope.\n'
        'Existing upstream rights and notices remain intact.\n'
        'Licensor of approved original work: WGY (GitHub: wgy-wsx) <wgy@wsxdesk.com>.\n'
        'For the original PolyForm-covered portions only:\n'
        'Required Notice: Copyright (c) 2026 WGY (GitHub: wgy-wsx) <wgy@wsxdesk.com>\n'
        'Original GPL tools/helpers: GPL-2.0-or-later; see the complete GPL text.\n'
        'Original MIT expression exceptions: see WSX-MIT.txt and OUTPUT-LICENSES.md.\n'
        'Installed full license texts are under reference-texts/; repository paths refer to the source recipe tree.\n'
        'A generator license does not automatically apply to its output.\n'
        'Public image distribution is not approved; private artifact policy is separate.\n')
    for name in ('LICENSE','LICENSE-MAP.md'):
        (notices/name).write_bytes((root/name).read_bytes())
    for name in ('OUTPUT-LICENSES.md','PRIVATE-ARTIFACTS.md'):
        (notices/name).write_bytes((root/'docs/licensing'/name).read_bytes())
    return report


def package_evidence(rootfs):
    """Capture installed metadata and notice bytes, without inferring permissions."""
    rootfs = rootfs.resolve(strict=True)

    def regular(path):
        if path.is_symlink() or not path.resolve().is_relative_to(rootfs) or not path.is_file():
            raise ValueError('Unsafe package evidence file: ' + str(path))
        return dict(path=str(path.relative_to(rootfs)), sha256=sha(path))

    database = rootfs/'var/lib/pacman/local'
    if database.is_symlink() or not database.resolve().is_relative_to(rootfs):
        raise ValueError('Unsafe installed package database')
    packages = []
    identities = set()
    for directory in sorted(database.iterdir()) if database.is_dir() else []:
        if directory.name == 'ALPM_DB_VERSION' and directory.is_file():
            continue
        if directory.is_symlink() or not directory.is_dir():
            raise ValueError('Unexpected installed package database entry')
        desc = directory/'desc'
        evidence = [regular(desc), regular(directory/'files')]
        fields = {}; key = None
        for line in desc.read_text().splitlines():
            if line.startswith('%') and line.endswith('%'):
                key = line[1:-1]
                if key in fields:
                    raise ValueError('Duplicate installed package metadata field')
                fields[key] = []
            elif line and key is not None:
                fields[key].append(line)
        for key in ('NAME', 'VERSION'):
            if len(fields.get(key, [])) != 1:
                raise ValueError('Missing/ambiguous installed package ' + key)
        name = fields['NAME'][0]
        if name in identities:
            raise ValueError('Duplicate installed package identity: ' + name)
        identities.add(name)
        packages.append(dict(name=name, version=fields['VERSION'][0],
                             declared_licenses=fields.get('LICENSE', []), metadata=evidence,
                             license_review='pending'))
    # Keep shared and package-specific license texts without guessing their owners.
    notices = []
    license_root = rootfs/'usr/share/licenses'
    if license_root.is_symlink() or not license_root.resolve().is_relative_to(rootfs):
        raise ValueError('Unsafe installed license directory')
    for path in sorted(license_root.rglob('*')):
        if path.relative_to(license_root).parts[0] == 'wsx-components':
            continue  # Already bound separately; avoid hashing this report itself.
        if not path.parent.resolve().is_relative_to(rootfs):
            raise ValueError('Installed license parent escapes rootfs')
        if path.is_symlink():
            notices.append(dict(path=str(path.relative_to(rootfs)), symlink=str(path.readlink())))
        elif path.is_file():
            notices.append(regular(path))
    return dict(packages=packages, installed_license_files=notices,
                evidence_present=bool(packages), license_review='pending',
                distribution_allowed=False,
                scope='Pacman local metadata and /usr/share/licenses; declarations are not permission conclusions. '
                      'Unmanaged assets, package source availability and trademark rights require separate review.')


def image_report(rootfs, work):
    # The caller verifies the original material receipt before invoking this function.
    rootfs = rootfs.resolve(strict=True)
    original = work/'component-materials/notices'
    if not original.resolve().is_relative_to(work.resolve()):
        raise ValueError('Source notice directory escapes workspace')
    target = rootfs/'usr/share/licenses/wsx-components'
    if not target.resolve().is_relative_to(rootfs):
        raise ValueError('Image notice directory escapes rootfs')
    for name in ('MODULE-LICENSES.json', 'MODULE-NOTICES.txt', 'LICENSE', 'LICENSE-MAP.md',
                 'OUTPUT-LICENSES.md', 'PRIVATE-ARTIFACTS.md'):
        if (original/name).is_symlink() or (target/name).is_symlink() or (target/name).read_bytes() != (original/name).read_bytes():
            raise ValueError('Installed module notice differs from source evidence: ' + name)
    mapping = json.loads((target/'MODULE-LICENSES.json').read_text())
    records = []
    for output in mapping['outputs']:
        found = set()
        for pattern in output['installed_paths']:
            # pathlib glob("prefix/**") alone lists directories, not every file.
            pattern = pattern+'/*' if pattern.endswith('/**') else pattern
            if Path(pattern).is_absolute() or '..' in Path(pattern).parts:
                raise ValueError('Unsafe installed output pattern')
            matches = list(rootfs.glob(pattern))
            if any(not p.parent.resolve().is_relative_to(rootfs) for p in matches):
                raise ValueError('Image output parent escapes rootfs')
            if not any(p.is_file() or p.is_symlink() for p in matches):
                raise ValueError('Declared installed output is missing: ' + pattern)
            for path in matches:
                if path.is_dir() and not path.is_symlink():
                    continue
                name = str(path.relative_to(rootfs))
                if name in found:
                    continue
                found.add(name)
                if path.is_symlink():
                    records.append(dict(path=name, output=output['id'], symlink=str(path.readlink())))
                elif path.is_file():
                    records.append(dict(path=name, output=output['id'], sha256=sha(path)))
    report = dict(schema_version=1, profile=mapping['profile'], license_grant=mapping['license_grant'],
                  release_ready=False, module_map_sha256=sha(target/'MODULE-LICENSES.json'),
                  scope='Declared WSX/private outputs plus installed package and license evidence; legal review pending',
                  package_evidence=package_evidence(rootfs),
                  files=sorted(records, key=lambda r: r['path']))
    return report


def write_image_map(rootfs, work):
    report = image_report(rootfs, work)
    destination = rootfs/'usr/share/licenses/wsx-components/IMAGE-LICENSES.json'
    if destination.exists():
        raise ValueError('Image license map already exists')
    destination.write_text(json.dumps(report, indent=2)+'\n')
    return report


def verify_image_map(rootfs, work):
    path = rootfs/'usr/share/licenses/wsx-components/IMAGE-LICENSES.json'
    if path.is_symlink() or json.loads(path.read_text()) != image_report(rootfs, work):
        raise ValueError('Installed module license binding changed')
