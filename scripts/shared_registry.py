"""Read source-only OCI artifacts anonymously from the approved GHCR package."""
import hashlib
import json
import re
from urllib.parse import urlencode
from urllib.request import Request, urlopen

PACKAGE = 'wsld-wsx/wsx-rootfs/graphics-sources'
IMAGE = 'ghcr.io/' + PACKAGE
MANIFEST_TYPE = 'application/vnd.oci.image.manifest.v1+json'
TITLE = 'org.opencontainers.image.title'


def validate_image(image):
    if not re.fullmatch(re.escape(IMAGE) + r'@sha256:[0-9a-f]{64}', image):
        raise ValueError('Expected an immutable digest in the source-only package')


def request(path, token, accept=None):
    headers = {'Authorization': 'Bearer ' + token, 'User-Agent': 'WSX-source-delivery/2'}
    if accept:
        headers['Accept'] = accept
    return urlopen(Request('https://ghcr.io/v2/' + PACKAGE + '/' + path, headers=headers), timeout=120)


def token():
    query = urlencode({'service': 'ghcr.io', 'scope': 'repository:' + PACKAGE + ':pull'})
    with urlopen(Request('https://ghcr.io/token?' + query, headers={'User-Agent': 'WSX-source-delivery/2'}), timeout=60) as response:
        return json.load(response)['token']


def manifest(pin, names):
    image = pin['image']
    validate_image(image)
    auth = token()
    digest = image.rsplit('@', 1)[1]
    with request('manifests/' + digest, auth, MANIFEST_TYPE) as response:
        data = response.read(16 * 1024 * 1024 + 1)
    if len(data) > 16 * 1024 * 1024 or 'sha256:' + hashlib.sha256(data).hexdigest() != digest:
        raise ValueError('OCI source manifest digest mismatch')
    document = json.loads(data)
    if document.get('schemaVersion') != 2 or document.get('mediaType') != MANIFEST_TYPE:
        raise ValueError('Unsupported OCI source manifest')
    layers = document.get('layers')
    if not isinstance(layers, list):
        raise ValueError('Missing OCI source layers')
    result = {}
    for layer in layers:
        name = layer.get('annotations', {}).get(TITLE)
        size, layer_digest = layer.get('size'), layer.get('digest', '')
        if (name not in names or name in result or type(size) is not int or size < 0
                or not re.fullmatch(r'sha256:[0-9a-f]{64}', layer_digest)):
            raise ValueError('Invalid or duplicate OCI source layer')
        result[name] = layer
    if set(result) != set(names):
        raise ValueError('Incomplete OCI source package')
    return auth, result


def fetch(auth, layer, destination):
    digest = hashlib.sha256()
    total = 0
    with request('blobs/' + layer['digest'], auth) as response:
        while chunk := response.read(1024 * 1024):
            total += len(chunk)
            if total > layer['size']:
                raise ValueError('OCI source layer exceeds declared size')
            digest.update(chunk)
            destination.write(chunk)
    if total != layer['size'] or 'sha256:' + digest.hexdigest() != layer['digest']:
        raise ValueError('OCI source layer digest or size mismatch')
