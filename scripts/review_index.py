"""Create a compact, honest review index within the published source record."""
import os
import re


def create(manifest, sources):
    delivery = sources['component_source_delivery']
    packages = sources['rootfs_packages']
    known = []
    for line in packages:
        parts = line.split(None, 1)
        if len(parts) == 2 and parts[0] == 'libfdk-aac':
            known.append(dict(package=parts[0], version=parts[1],
                discovery_url='https://archlinux.org/packages/extra/x86_64/libfdk-aac/',
                corresponding_source_status='not_verified',
                note='Discovery link only; verify exact version and applicable source delivery.'))
    sha = os.environ.get('GITHUB_SHA', '')
    workflow = dict(repository=os.environ.get('GITHUB_REPOSITORY') or None,
                    commit=sha if re.fullmatch(r'[0-9a-f]{40}', sha) else None,
                    run_id=os.environ.get('GITHUB_RUN_ID') or None,
                    run_attempt=os.environ.get('GITHUB_RUN_ATTEMPT') or None)
    return dict(schema_version=1,
        image=dict(asset=manifest['asset_name'], sha256=manifest['sha256'],
                   recipe_commit=manifest['build_commit'], build_identity=manifest['build_identity']),
        workflow=workflow,
        package_inventory='sources.json#/rootfs_packages',
        package_repositories='sources.json#/rootfs_repositories',
        image_recipe='image-recipe.tar.gz',
        graphics_receipt='component-source.json', graphics_index='graphics-sources.json',
        graphics_source=delivery.get('shared_source'),
        known_source_requirements=known,
        source_completeness='not_verified', license_review='not_completed',
        note='An index of retained evidence, not a license approval or proof of corresponding source availability.')
