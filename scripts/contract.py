"""Versioned release contract and a conservative client-side resolution example."""
import hashlib
import json
import re
from payload_contract import asset_names

DISTRIBUTIONS = ('wsx-omarchy', 'wsx-cachyos-plasma')
SEMVER = r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)'
IMAGE = re.compile(SEMVER + r'-r([1-9][0-9]*)\Z')
HEX = re.compile(r'[0-9a-f]{64}\Z')


def image_order(value):
    match = IMAGE.fullmatch(value)
    if not match:
        raise ValueError('Unsupported image version: ' + value)
    return tuple(map(int, match.groups()))


def parse_install(value):
    for distro in sorted(DISTRIBUTIONS, key=len, reverse=True):
        if value == distro:
            return distro, None
        if value.startswith(distro + '-'):
            suffix = value[len(distro) + 1:]
            image_order(suffix)
            return distro, suffix
    raise ValueError('Unknown distribution ID')


def identity(inputs):
    return hashlib.sha256(json.dumps(inputs, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=True).encode()).hexdigest()


def validate(manifest):
    asset_names(manifest)  # Reject unknown source-delivery versions.
    if type(manifest['schema_version']) is not int or manifest['schema_version'] != 1:
        raise ValueError('Unsupported schema')
    distro = manifest['distribution_id']
    if distro not in DISTRIBUTIONS:
        raise ValueError('Unknown distribution')
    image = manifest['image_version']
    order = image_order(image)
    if type(manifest['wsx_revision']) is not int or manifest['wsx_revision'] != order[3]:
        raise ValueError('Revision mismatch')
    if manifest['upstream_release'].removeprefix('v') != '.'.join(map(str, order[:3])):
        raise ValueError('Upstream version mismatch')
    if manifest['architecture'] != 'x86_64' or manifest['archive_format'] != 'tar.zst':
        raise ValueError('Unsupported architecture/archive')
    if manifest['asset_name'] != f'{distro}-{image}-x86_64.rootfs.tar.zst':
        raise ValueError('Asset name mismatch')
    for key in ('sha256', 'build_identity'):
        if not HEX.fullmatch(manifest[key]):
            raise ValueError('Invalid digest: ' + key)
    for key in ('build_commit', 'upstream_commit'):
        if not re.fullmatch(r'[0-9a-f]{40}', manifest[key]):
            raise ValueError('Invalid commit: ' + key)
    for key in ('compressed_size', 'unpacked_size', 'installation_space_required'):
        if type(manifest[key]) is not int or manifest[key] <= 0:
            raise ValueError('Invalid size: ' + key)
    if manifest['installation_space_required'] < manifest['unpacked_size']:
        raise ValueError('Insufficient installation estimate')
    if not isinstance(manifest['graphics_components'], list) or not manifest['graphics_components']:
        raise ValueError('Missing graphics closure')
    for component in manifest['graphics_components']:
        if not component['name'] or not component['version'] or not HEX.fullmatch(component['inputs_sha256']):
            raise ValueError('Incomplete graphics component')
    cpu = manifest.get('cpu_requirements')
    if distro == 'wsx-cachyos-plasma' and cpu != {'architecture_level': 'x86-64-v3'}:
        raise ValueError('Missing or unsupported CPU requirements')
    if cpu is not None and cpu != {'architecture_level': 'x86-64-v3'}:
        raise ValueError('Unsupported CPU requirements')
    if not isinstance(manifest['kernel_requirements'], dict) or not manifest['kernel_requirements']:
        raise ValueError('Missing kernel contract')
    if manifest['guest_interface_abi'] is not None and (type(manifest['guest_interface_abi']) is not int or manifest['guest_interface_abi'] < 1):
        raise ValueError('Invalid Guest ABI')
    minimum = manifest['minimum_wsx_core_version']
    if minimum is not None and not re.fullmatch(SEMVER, minimum):
        raise ValueError('Invalid minimum core version')
    statuses = manifest['validation']
    for stage in ('build', 'offline', 'wsl_boot', 'gpu_first_frame', 'desktop', 'stability'):
        if statuses[stage] not in ('passed', 'failed', 'not_run'):
            raise ValueError('Invalid validation status')
    if statuses['build'] != 'passed' or statuses['offline'] != 'passed':
        raise ValueError('Candidate has not passed basic validation')
    return manifest


def resolve(request, releases, compatible):
    """Caller supplies fetched and asset-verified manifests, never anonymous Drafts."""
    distro, requested = parse_install(request)
    candidates = []
    for release in releases:
        if release.get('draft', True) or release.get('prerelease', True):
            continue
        manifest = release.get('manifest', {})
        if manifest.get('distribution_id') != distro:
            continue
        if requested and manifest.get('image_version') != requested:
            continue
        try:
            validate(manifest)
        except (KeyError, TypeError, ValueError):
            continue
        if release.get('tag_name') != distro + '-' + manifest['image_version']:
            continue
        if release.get('assets_verified') is not True:
            continue
        if manifest['guest_interface_abi'] is None or manifest['minimum_wsx_core_version'] is None:
            continue
        if any(manifest['validation'][s] != 'passed' for s in ('wsl_boot', 'gpu_first_frame', 'desktop')):
            continue
        if compatible(manifest):
            candidates.append(manifest)
    if not candidates:
        raise ValueError('Requested image is missing, incomplete, unverified or incompatible')
    return max(candidates, key=lambda m: image_order(m['image_version']))
