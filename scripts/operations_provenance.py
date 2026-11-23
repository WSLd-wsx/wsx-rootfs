# SPDX-License-Identifier: GPL-2.0-or-later OR Apache-2.0
"""Record the separate operations workflow commit when a build uses one."""
import os
import re


def repositories(environ=None):
    env = os.environ if environ is None else environ
    return tuple(name for key in ('WSX_OPERATIONS_REPOSITORY', 'WSX_LEGACY_OPERATIONS_REPOSITORY')
                 if (name := env.get(key, '')) and re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', name))


def attach(inputs, environ=None):
    env = os.environ if environ is None else environ
    commit = env.get('WSX_OPERATIONS_COMMIT', '')
    if not commit:
        return inputs
    repository = env.get('GITHUB_REPOSITORY') or env.get('WSX_OPERATIONS_REPOSITORY', '')
    if repository not in repositories(env) or not re.fullmatch('[0-9a-f]{40}', commit):
        raise ValueError('Exact approved operations repository and commit required')
    return dict(inputs, operations_repository=repository, operations_commit=commit)
