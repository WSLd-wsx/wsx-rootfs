"""Registry transport must preserve immutable origin and private access."""
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import component_registry as registry


class RegistryTests(unittest.TestCase):
    def test_operations_build_binds_recipe_and_workflow_commits(self):
        env = dict(GITHUB_REPOSITORY='WSLd-wsx/wsx-rootfs-ops', GITHUB_SHA='a'*40,
                   WSX_SOURCE_COMMIT='b'*40, WSX_COMPONENT_IMAGE=registry.OPS_IMAGE)
        self.assertEqual(registry.publication_origin(env),
                         (registry.OPS_IMAGE, 'WSLd-wsx/wsx-rootfs-ops', 'b'*40, 'a'*40))
        for changed in (dict(env, WSX_SOURCE_COMMIT='main'),
                        dict(env, GITHUB_SHA='bad'), dict(env, WSX_COMPONENT_IMAGE=registry.IMAGE),
                        dict(env, GITHUB_REPOSITORY='other/repo')):
            with self.assertRaises(ValueError):
                registry.publication_origin(changed)
        legacy = dict(GITHUB_REPOSITORY=registry.REPOSITORY, GITHUB_SHA='c'*40)
        self.assertEqual(registry.publication_origin(legacy), (registry.IMAGE, registry.REPOSITORY, 'c'*40, None))

    def test_registry_uses_separate_token_from_repository_api(self):
        env = {'GH_TOKEN': 'api-token', 'WSX_COMPONENT_REGISTRY_TOKEN': 'registry-token',
               'GITHUB_ACTOR': 'test-actor'}
        with patch.dict(os.environ, env, clear=True), patch.object(registry.subprocess, 'run') as run:
            with registry.docker_session():
                pass
        self.assertEqual(run.call_args.kwargs['input'], 'registry-token')

    def test_reference_rejects_mutable_tags_and_other_packages(self):
        registry.check_reference(registry.IMAGE + '@sha256:' + 'a' * 64)
        registry.check_reference(registry.OPS_IMAGE + '@sha256:' + 'b' * 64)
        for reference in (registry.IMAGE + ':latest', registry.IMAGE + '-other@sha256:' + 'a' * 64,
                          registry.IMAGE + '@sha256:bad', registry.OPS_IMAGE + ':latest',
                          'ghcr.io/other/wsx-rootfs-ops/graphics-components@sha256:' + 'a' * 64):
            with self.assertRaises(ValueError):
                registry.check_reference(reference)

    def test_labels_bind_profile_commit_and_run(self):
        pin = dict(source_commit='a' * 40, run_id=17)
        labels = {'org.opencontainers.image.source': 'https://github.com/' + registry.REPOSITORY,
                  'org.opencontainers.image.revision': pin['source_commit'],
                  'io.wsx.run-id': '17', 'io.wsx.profile': 'omarchy'}
        registry.validate_labels(labels, pin, 'omarchy')
        for key in labels:
            with self.assertRaises(ValueError):
                registry.validate_labels(dict(labels, **{key: 'wrong'}), pin, 'omarchy')

    def test_public_package_is_rejected_and_only_404_allows_creation(self):
        with patch.object(registry.subprocess, 'check_output', return_value=json.dumps(dict(full_name=registry.REPOSITORY,private=True)).encode()):
            for visibility in ('public', 'internal'):
                response = SimpleNamespace(returncode=0, stdout='HTTP/2.0 200 OK\n\n' + json.dumps(dict(visibility=visibility)))
                with patch.object(registry.subprocess, 'run', return_value=response), self.assertRaises(ValueError):
                    registry.require_private(allow_missing=True)
            for code in (403, 404):
                response = SimpleNamespace(returncode=1, stdout=f'HTTP/2.0 {code} error\n\n{{}}')
                with patch.object(registry.subprocess, 'run', return_value=response):
                    if code == 404:
                        registry.require_private(allow_missing=True)
                    else:
                        with self.assertRaises(ValueError):
                            registry.require_private(allow_missing=True)

    def test_public_repository_requires_existing_private_package(self):
        with patch.object(registry.subprocess,'check_output',return_value=json.dumps(dict(full_name=registry.REPOSITORY,private=False)).encode()):
            response=SimpleNamespace(returncode=0,stdout='HTTP/2.0 200 OK\n\n'+json.dumps(dict(visibility='private')))
            with patch.object(registry.subprocess,'run',return_value=response):
                registry.require_private()
            response=SimpleNamespace(returncode=1,stdout='HTTP/2.0 404 error\n\n{}')
            with patch.object(registry.subprocess,'run',return_value=response),self.assertRaises(ValueError):
                registry.require_private(allow_missing=True)
