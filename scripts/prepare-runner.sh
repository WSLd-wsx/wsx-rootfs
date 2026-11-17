#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Reclaim unused SDKs only on an ephemeral GitHub-hosted Linux runner.
set -euo pipefail
[[ ${GITHUB_ACTIONS:-} == true && ${RUNNER_OS:-} == Linux ]]
[[ ${RUNNER_ENVIRONMENT:-} == github-hosted ]]
[[ -n ${GITHUB_WORKSPACE:-} && "$PWD" == "$GITHUB_WORKSPACE" ]]
df -h .
# These fixed SDK paths are not used by the pinned Arch builder or host checks.
for path in /usr/local/lib/android /usr/share/dotnet /opt/ghc; do
  if [[ -d "$path" && ! -L "$path" ]]; then
    sudo du -sh "$path"
    sudo rm -rf -- "$path"
  fi
done
df -h .
