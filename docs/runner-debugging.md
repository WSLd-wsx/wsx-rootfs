# Actor-key runner debugging

The user requested mxschmitt/action-tmate for live inspection of hosted runners.
The action is pinned to 35b54afac29c97fb54faba5b513f8fbd1882f113 (v3). Its source
and inputs were inspected. Ubuntu's signed apt repositories supply tmate and
OpenSSH; the action's unchecked static-binary download is disabled.

Manually dispatch omarchy.yml with debug_enabled=true. Scheduled runs do not
start a tunnel. The session requires the triggering actor's registered GitHub
SSH keys; absence is an error, never an anonymous-access fallback. A matching
private key remains on the operator's machine and is never uploaded.

The detached session runs alongside the build. Retrieve runner-debug-connection
with authenticated gh while the job is active; its runner-debug.json identifies
the exact run, commit and SSH address. This avoids depending on incomplete job
logs being downloadable through the GitHub API. Connection metadata expires as
an Actions artifact after one day. The server host key must be verified against
the upstream tmate fingerprint before connecting.

```sh
gh workflow run omarchy.yml --repo WSLd-wsx/wsx-rootfs --ref main \
  -f revision=5 -f debug_enabled=true
# Substitute the exact returned run ID and a fresh local directory.
gh run download RUN_ID --repo WSLd-wsx/wsx-rootfs \
  --name runner-debug-connection --dir DEBUG_DIRECTORY
```

Inspect disk use, CPU/memory and the owned wsx-rootfs-builder container through
SSH. A failed pre-archive builder is retained for up to ten minutes for inspection;
create `continue` in GITHUB_WORKSPACE (or /continue) to release it sooner. At job
completion, the action waits up to ten minutes for a connection; an attached
session can hold it until the job timeout. Exit the session and create continue
when finished. Cancelled runs release the ephemeral runner normally.

Debug runs never upload candidate-payload and never execute Draft publication.
This also prevents the publication-retry entry from publishing their artifacts.
Changes discovered interactively must be committed and validated in an ordinary
non-debug run before release. Debugging is not GPU/WSL acceptance and must not
modify the reference repository, deployed desktops, WSL or Windows services.

A workflow edit cannot add a session to a runner that is already executing an
older commit. Preserve that run and start a separate manual diagnostic when needed.
