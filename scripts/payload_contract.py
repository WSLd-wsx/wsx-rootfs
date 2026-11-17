"""Versioned asset names shared by build preflight, finalizers and publication."""
SOURCE_ASSETS = ('component-sources.tar', 'component-materials.json', 'component-source.json')
SHARED_SOURCE_ASSETS = ('image-recipe.tar.gz', 'graphics-sources.json', 'component-source.json')


def source_asset_names(manifest):
    if 'source_delivery_schema' not in manifest:
        return ()
    version = manifest['source_delivery_schema']
    if type(version) is not int or version not in (1, 2):
        raise ValueError('Unsupported source delivery schema')
    return SOURCE_ASSETS if version == 1 else SHARED_SOURCE_ASSETS


def asset_names(manifest):
    names = [manifest['asset_name'], 'manifest.json', 'SHA256SUMS', 'sources.json', 'validation.json']
    names.extend(source_asset_names(manifest))
    return names


def validate_completion(manifest, marker):
    if (marker.get('schema_version') != 1
            or marker.get('build_identity') != manifest['build_identity']
            or set(marker.get('assets', {})) != set(asset_names(manifest))):
        raise ValueError('Incomplete completion marker or identity mismatch')
    if marker['assets'][manifest['asset_name']] != {'size': manifest['compressed_size'], 'sha256': manifest['sha256']}:
        raise ValueError('Completion archive contract mismatch')
