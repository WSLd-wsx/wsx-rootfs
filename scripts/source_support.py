"""Check the local source recipe closure without claiming compiler acceptance."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
def require_source_recipe(distribution):
    if distribution == 'wsx-omarchy':
        return
    if distribution != 'wsx-cachyos-plasma':
        raise ValueError('Unsupported distribution: ' + distribution)
    pin = json.loads((ROOT/'components/sources.json').read_text()).get('kwin', {})
    if pin.get('version') != '6.8.1' or len(pin.get('sha256', '')) != 64:
        raise ValueError('Missing pinned KWin 6.8.1 source')
    for name in ('scripts/build-kwin.py', 'distros/cachyos-plasma/build-components.sh',
                 'distros/cachyos-plasma/build-dependencies.txt',
                 'vendor/wsx-proto/guest-opaque/prepare-kwin.py',
                 'vendor/wsx-proto/guest-opaque/kwin-opaque-consumer.patch'):
        if not (ROOT/name).is_file():
            raise ValueError('Incomplete source recipe: ' + name)
