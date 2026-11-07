# SPDX-License-Identifier: GPL-2.0-or-later
"""Record the separate operations workflow commit when a build uses one."""
import os
import re


def attach(inputs, environ=None):
    env = os.environ if environ is None else environ
    commit = env.get('WSX_OPERATIONS_COMMIT', '')
    repository = env.get('WSX_OPERATIONS_REPOSITORY', '')
    if not commit and not repository:
        return inputs
    if repository != 'WSLd-wsx/wsx-rootfs-ops' or not re.fullmatch('[0-9a-f]{40}', commit):
        raise ValueError('Exact approved operations repository and commit required')
    return dict(inputs, operations_repository=repository, operations_commit=commit)
