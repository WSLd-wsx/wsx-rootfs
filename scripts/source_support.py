"""Check the local source recipe closure without claiming compiler acceptance."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
KWIN_SOURCE_LOCK = 'distros/cachyos-plasma/kwin-source.json'
ARCH_SNAPSHOT = 'distros/cachyos-plasma/arch-snapshot'
PROFILE_COMPONENTS = {
    'omarchy': {'mesa', 'venus', 'aquamarine', 'hyprland', 'udis86', 'glaze'},
    'cachyos-plasma': {'mesa', 'venus', 'kwin'},
}


def kwin_lock(root):
    path = root/KWIN_SOURCE_LOCK
    if not path.is_file():
        raise ValueError('Missing pinned KWin source: ' + KWIN_SOURCE_LOCK)
    return json.loads(path.read_text())


def component_pins(root, profile):
    shared = json.loads((root/'components/sources.json').read_text())
    if profile == 'cachyos-plasma':
        shared['kwin'] = {name: value for name, value in kwin_lock(root).items() if name != 'packages'}
    required = PROFILE_COMPONENTS[profile]
    missing = required.difference(shared)
    if missing:
        raise ValueError('Missing source pins for ' + profile + ': ' + ', '.join(sorted(missing)))
    return {name: pin for name, pin in shared.items() if name in required}


def require_source_recipe(distribution):
    if distribution == 'WSX-omarchy':
        return
    if distribution != 'WSX-cachyos-plasma':
        raise ValueError('Unsupported distribution: ' + distribution)
    pin = kwin_lock(ROOT)
    if not pin.get('version') or len(pin.get('sha256', '')) != 64:
        raise ValueError('Missing pinned KWin source')
    for name in (ARCH_SNAPSHOT, 'scripts/build-kwin.py', 'distros/cachyos-plasma/build-components.sh',
                 'distros/cachyos-plasma/build-dependencies.txt',
                 'vendor/wsx-guest-sources/guest-opaque/prepare-kwin.py',
                 'vendor/wsx-guest-sources/guest-opaque/kwin-opaque-consumer.patch'):
        if not (ROOT/name).is_file():
            raise ValueError('Incomplete source recipe: ' + name)
