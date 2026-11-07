#!/usr/bin/env python3
"""Expose bounded compiler-log progress without changing the build command."""
import argparse
from pathlib import Path
import subprocess
import time


def snapshot(directory, previous):
    current = {}
    for path in sorted(directory.glob('*/*.log')):
        if path.is_symlink() or not path.is_file():
            continue
        try:
            info = path.stat()
            key = str(path.relative_to(directory))
            current[key] = (info.st_size, info.st_mtime_ns)
            if previous.get(key) == current[key]:
                continue
            with path.open('rb') as stream:
                stream.seek(max(0, info.st_size - 4096))
                tail = stream.read(4096).decode('utf-8', errors='replace').splitlines()[-8:]
            print(f'[build log] {key}: {info.st_size} bytes', flush=True)
            for line in tail:
                # Indentation keeps compiler text from becoming an Actions command.
                print('  '+line, flush=True)
        except (FileNotFoundError, PermissionError):
            print('[build log] temporarily unreadable: '+str(path), flush=True)
    return current


def watch(command, directory, interval=30):
    started = time.monotonic()
    previous = {}
    print('[build monitor] started; process liveness is not proof of compiler progress', flush=True)
    process = subprocess.Popen(command)
    try:
        while True:
            try:
                code = process.wait(timeout=interval)
                snapshot(directory, previous)
                print(f'[build monitor] exited {code}; elapsed {int(time.monotonic()-started)}s', flush=True)
                return code
            except subprocess.TimeoutExpired:
                previous = snapshot(directory, previous)
                print(f'[build monitor] process alive; elapsed {int(time.monotonic()-started)}s; '
                      'unchanged log sizes may mean no visible progress', flush=True)
    except BaseException:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command:
        parser.error('A build command is required')
    raise SystemExit(watch(command, args.directory))
