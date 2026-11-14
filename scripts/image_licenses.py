"""Image-phase license binding for external Guest v2 adapters."""
import json
from pathlib import Path
from product_licenses import sha, package_evidence


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
    # The retained component receipt describes the earlier image layout. The
    # Omarchy v2 image no longer installs these independently supplied adapters.
    external_omarchy = {
        'desktop-omarchy': 'usr/lib/wsx/runtime/desktop.py',
        'guest-omarchy': 'usr/bin/wsx-guest',
        'protocol-guest-protocol': 'usr/lib/wsx/guest-protocol.py',
        'protocol-device-view': 'usr/lib/wsx/device-view.py',
        'protocol-protocol-display': 'usr/lib/wsx/protocol-display.py',
        'protocol-protocol-retirement': 'usr/lib/wsx/protocol-retirement.py',
    }
    for output in mapping['outputs']:
        if mapping['profile'] == 'omarchy' and output['id'] in external_omarchy:
            path = external_omarchy[output['id']]
            if output['installed_paths'] != [path]:
                raise ValueError('Unexpected external Guest output mapping: ' + output['id'])
            if (rootfs/path).exists() or (rootfs/path).is_symlink():
                raise ValueError('External Guest adapter unexpectedly installed: ' + path)
            continue
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
