#!/usr/bin/env python3
"""Remove an isolated image's build-time pacman identity after sanitization."""
import argparse
from pathlib import Path
import shutil


def reset(root):
    root = root.resolve(strict=True)
    if str(root) in ('/', '/output', '/workspace') or not (root/'etc/os-release').is_file():
        raise ValueError('Refusing a non-image target')
    parent = (root/'etc/pacman.d').resolve(strict=True)
    if not parent.is_relative_to(root) or not parent.is_dir():
        raise ValueError('Pacman keyring parent escapes image')
    keyring = parent/'gnupg'
    if keyring.is_symlink() or (keyring.exists() and not keyring.is_dir()):
        raise ValueError('Unexpected keyring path')
    if keyring.exists():
        shutil.rmtree(keyring)
    keyring.mkdir(mode=0o700)
    keyring.chmod(0o700)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('root', type=Path)
    reset(p.parse_args().root)


if __name__ == '__main__':
    main()
