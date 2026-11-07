# Independent local rootfs build

The source repository contains the recipes and build/validation scripts. The
private `wsx-rootfs-ops` repository provides hosted orchestration and is not
needed for a local build. Build on a compatible Linux host with Docker, Python 3,
`python3-jsonschema`, `zstd`, `tar`, `acl`, `libcap` tools and GitHub CLI. The
builder uses a privileged container and substantial storage; use an isolated
machine and verify available disk capacity before starting. The build does not
import, initialize or start a WSL distribution.

Private component packages and source materials require appropriately scoped
read access. Authenticate `gh` without embedding credentials in commands, and
configure `GH_TOKEN` and, if the registry credential differs,
`WSX_COMPONENT_REGISTRY_TOKEN` in a secure process environment. Set
`WSX_PRIVATE_SOURCE=1` only while the approved source repository is private;
unset it for a public source repository. The verified, pinned component and
shared-source inputs must already exist. No package signature check is disabled.

From a clean checkout, use a new empty `out` directory. For Omarchy:

```sh
mkdir out
python3 scripts/desktop_contract.py --check-pin
python3 scripts/check-shared-sources.py --profile omarchy
python3 scripts/prepare-build.py --version 4.0.6 --revision 1 --repo WSLd-wsx/wsx-rootfs --output out/build.json
python3 scripts/reuse-components.py --profile omarchy --repo WSLd-wsx/wsx-rootfs --work out
image=$(python3 -c 'import json; print(json.load(open("components/builder.json"))["image"])')
docker run -d --name wsx-local-builder --privileged -v "$PWD:/workspace:ro" -v "$PWD/out:/output" "$image" sleep infinity
docker exec wsx-local-builder bash /workspace/distros/omarchy/bootstrap-rootfs.sh
docker exec wsx-local-builder bash /workspace/distros/omarchy/build-rootfs.sh
docker stop wsx-local-builder
docker rm wsx-local-builder
python3 scripts/archive_policy.py --repo WSLd-wsx/wsx-rootfs --work out
sudo --preserve-env=GH_TOKEN,WSX_PRIVATE_SOURCE /usr/bin/python3 scripts/finalize.py out
```

For CachyOS replace the preparation/build/finalization commands with:

```sh
mkdir out
python3 scripts/desktop_contract.py --check-pin
python3 scripts/check-shared-sources.py --profile cachyos-plasma
python3 scripts/prepare-cachyos.py --snapshot 2026.11.5 --revision 1 --repo WSLd-wsx/wsx-rootfs --output out/build.json
python3 scripts/reuse-components.py --profile cachyos-plasma --repo WSLd-wsx/wsx-rootfs --work out
image=$(python3 -c 'import json; print(json.load(open("components/builder.json"))["image"])')
docker run -d --name wsx-local-builder --privileged -v "$PWD:/workspace:ro" -v "$PWD/out:/output" "$image" sleep infinity
docker exec wsx-local-builder bash /workspace/distros/cachyos-plasma/bootstrap-rootfs.sh
docker exec wsx-local-builder bash /workspace/distros/cachyos-plasma/configure-rootfs.sh
docker stop wsx-local-builder
docker rm wsx-local-builder
python3 scripts/archive_policy.py --repo WSLd-wsx/wsx-rootfs --work out
sudo --preserve-env=GH_TOKEN,WSX_PRIVATE_SOURCE /usr/bin/python3 scripts/finalize-cachyos.py out
```

Versions above are examples, not instructions to overwrite or publish an existing
release. The prepare scripts reject a conflicting immutable version. A build may
need a new revision and a fresh full archive comparison. `out/payload` holds the
local candidate when finalization succeeds. Independently run the admission and
source/license checks before any publication. Building does not establish WSL,
GPU, input, desktop or long-term stability acceptance. If a command fails, keep
its diagnostics and clean up only the container created for this build.
