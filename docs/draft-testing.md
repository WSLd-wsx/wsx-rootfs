# Draft testing handoff

A completed Draft is an offline-validated candidate, not a verified desktop.
Use a disposable new WSL distribution; do not replace an existing instance.
The new Guest ABI must first be integrated with a matching wsx-core host/module
bundle. A null minimum core version explicitly means that this integration has
not established a compatible released client version.

## Download and verify

Use an account with repository access. Draft assets are not anonymous installer
inputs, and neither normal wsld.exe install form selects a Draft.

```sh
# Replace TAG with the exact completed candidate tag reported by the build.
mkdir candidate
cd candidate
gh release download TAG --repo WSLd-wsx/wsx-rootfs
sha256sum --check SHA256SUMS
python3 - <<'PY'
import hashlib, json
from pathlib import Path
m = json.loads(Path('manifest.json').read_text())
c = json.loads(Path('completion.json').read_text())
assert c['build_identity'] == m['build_identity']
expected = {m['asset_name'], 'manifest.json', 'SHA256SUMS', 'sources.json', 'validation.json'}
assert set(c['assets']) == expected
for name, item in c['assets'].items():
    assert Path(name).name == name
    p = Path(name)
    assert p.stat().st_size == item['size']
    with p.open('rb') as stream:
        assert hashlib.file_digest(stream, 'sha256').hexdigest() == item['sha256']
print('Complete payload verified')
PY
zstd --test *.rootfs.tar.zst
zstd --decompress --keep *.rootfs.tar.zst
```

Provide the uncompressed tar to wsx-core's import path or manually use
`wsl.exe --import <new-name> <new-install-directory> <tar-path> --version 2`.
WSL is not assumed to accept zstd directly. Do not execute install commands
against an existing distribution directory. Keep the original compressed asset,
manifest, checksums and completion receipt for traceability.

## First boot and integration

Enter the new instance as root and initialize it interactively:

```sh
wsx-guest initialize --user YOUR_USER --timezone YOUR_AREA/YOUR_CITY
```

The command prompts for a password without placing it in command arguments.
Choose an installed UTF-8 locale with `--locale` if needed. Verify ordinary sudo
and Polkit authentication with the initialized account. Never enable universal
passwords or passwordless policies to work around a failed test.

Follow [Guest ABI 1](guest-abi.md) for runtime preparation. Core must discover the
actual instance, device and endpoints, negotiate the sharing path, and verify
kernel/module compatibility before starting the desktop. The image alone does
not create the independent Windows host or supply matching kernel modules.

Record each acceptance level separately: WSL systemd boot and initialization;
real GPU first frame; menus, terminal, browser, fonts, Xwayland, authentication,
network and audio; normal session stop/restart; sustained stability. Record the
actual GPU, Windows driver, WSL kernel, module hashes, core build and input
manifest. Iris Xe evidence does not establish RTX acceptance, or vice versa.
Do not reinterpret opaque memory as a DRM modifier, enable staging, restart
WSL/services, or unload a failed retained owner as an implicit test recovery.
Preserve failed logs and instances for diagnosis.
