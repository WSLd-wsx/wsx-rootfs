#!/usr/bin/env python3
"""Pack a sanitized tree with GNU tar and verify extracted metadata and contents."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
import time

FORBIDDEN_CONTENT = ('proc', 'sys', 'dev', 'run', 'tmp', 'var/tmp', 'var/cache', 'root', 'home')


def inventory(root):
    result = {}
    links = {}
    for path in [root, *sorted(root.rglob('*'))]:
        relative = str(path.relative_to(root))
        s = path.lstat()
        item = dict(mode=s.st_mode, uid=s.st_uid, gid=s.st_gid, mtime_ns=s.st_mtime_ns,
                    xattrs={k: os.getxattr(path, k, follow_symlinks=False).hex()
                            for k in os.listxattr(path, follow_symlinks=False)})
        if stat.S_ISREG(s.st_mode):
            with path.open('rb') as stream:
                item['sha256'] = hashlib.file_digest(stream, 'sha256').hexdigest()
            item['size'] = s.st_size
            if s.st_nlink > 1:
                item['hardlink_group'] = links.setdefault((s.st_dev, s.st_ino), relative)
        elif stat.S_ISLNK(s.st_mode):
            item['target'] = os.readlink(path)
        elif not stat.S_ISDIR(s.st_mode):
            raise ValueError('Special file in rootfs: ' + relative)
        result[relative] = item
    return result


def check_hygiene(root):
    for relative in FORBIDDEN_CONTENT:
        path = root/relative
        if path.is_symlink() or (path.exists() and (not path.is_dir() or any(path.iterdir()))):
            raise ValueError('Runtime/private/cache directory is not empty: ' + relative)
    for path in root.rglob('*'):
        if path.is_symlink():
            continue
        relative = str(path.relative_to(root))
        if path.name in ('.git', '.ssh', '.aws', '.netrc', '.npmrc') or path.name.startswith('ssh_host_'):
            raise ValueError('Credential or build identity path: ' + relative)
        if relative in ('etc/machine-id', 'var/lib/dbus/machine-id') and path.stat().st_size:
            raise ValueError('Nonempty machine identity')
    # Refuse live submounts, even when their top-level directory looks harmless.
    for line in Path('/proc/self/mountinfo').read_text().splitlines():
        mount = Path(line.split()[4].replace('\\040', ' ')).resolve()
        if mount == root or root in mount.parents:
            raise ValueError('Build tree contains a mount: ' + str(mount))


def pack(root, output, level=15, threads=2, policy=None):
    root = root.resolve(strict=True); output = output.resolve()
    if root == output or root in output.parents or output.exists():
        raise ValueError('Output must be new and outside rootfs')
    if os.geteuid() != 0:
        raise ValueError('Root required to restore and verify ownership and capabilities')
    if level not in range(1, 20) or threads not in range(1, 5):
        raise ValueError('Compression resource limit exceeded')
    check_hygiene(root)
    mode = (policy or {}).get('mode', 'full')
    if mode not in ('full', 'stream'):
        raise ValueError('Unknown archive verification mode')
    if mode == 'stream' and not (policy or {}).get('evidence'):
        raise ValueError('Prior full verification evidence is required')
    before = inventory(root) if mode == 'full' else None
    logical_size = (sum(item.get('size', 0) for item in before.values()) if before is not None else
                    sum(p.lstat().st_size for p in root.rglob('*') if stat.S_ISREG(p.lstat().st_mode)))
    output.parent.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(output.parent).free < logical_size * (3 if mode == 'full' else 1) + 1024**3:
        raise ValueError('Insufficient disk for archive and extraction verification')
    options = ['--numeric-owner', '--acls', '--xattrs', '--xattrs-include=*']
    started = time.monotonic()
    partial = output.with_name(output.name + '.partial')
    try:
        with tempfile.TemporaryDirectory(prefix='wsx-archive-', dir=output.parent) as work:
            metrics = Path(work)/'compression.time'
            tar = subprocess.Popen(['tar', *options, '--format=pax', '-C', str(root), '-cpf', '-', '.'], stdout=subprocess.PIPE)
            try:
                with partial.open('xb') as stream:
                    compressed = subprocess.run(['/usr/bin/time', '-f', '%e %M', '-o', str(metrics),
                            'zstd', '-'+str(level), '-T'+str(threads), '-c'], stdin=tar.stdout, stdout=stream)
                tar.stdout.close()
                tar_code = tar.wait()
                if compressed.returncode or tar_code:
                    raise RuntimeError('Archive creation failed')
            finally:
                if tar.poll() is None:
                    tar.terminate(); tar.wait()
            subprocess.run(['zstd', '-t', str(partial)], check=True)
            verified = ['zstd_stream']
            if mode == 'full':
                extracted = Path(work)/'extracted'; extracted.mkdir()
                subprocess.run(['tar', *options, '--same-owner', '--same-permissions',
                                '--zstd', '-xpf', str(partial), '-C', str(extracted)], check=True)
                after = inventory(extracted)
                if before != after:
                    changed = sorted(k for k in before.keys() | after.keys() if before.get(k) != after.get(k))
                    raise ValueError('Extraction content/metadata mismatch: ' + ', '.join(changed[:20]))
                verified += ['uid','gid','mode','symlink','hardlink','xattr','acl','capability','file_hash']
            elapsed, peak_kib = metrics.read_text().split()
            report = dict(passed=True, logical_size=logical_size, compressed_size=partial.stat().st_size,
                          compression_seconds=float(elapsed), compression_peak_rss_kib=int(peak_kib),
                          total_seconds=time.monotonic()-started, level=level, threads=threads,
                          metadata_entries=len(before) if before is not None else None, verified=verified,
                          verification_mode=mode, recipe_fingerprint=(policy or {}).get('recipe_fingerprint'),
                          prior_full_verification=(policy or {}).get('evidence'))
        partial.rename(output)
        return report
    except BaseException:
        partial.unlink(missing_ok=True)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--level', type=int, default=15)
    parser.add_argument('--threads', type=int, default=2)
    args = parser.parse_args()
    report = pack(args.root, args.output, args.level, args.threads)
    args.output.with_suffix('.report.json').write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__':
    main()
