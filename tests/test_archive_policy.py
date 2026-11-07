"""Test evidence selection without treating simulated metadata as real acceptance."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import archive_policy as policy
from test_contract import manifest
from payload_contract import asset_names


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.build = {'inputs': {'distribution_id': 'wsx-omarchy', 'architecture': 'x86_64',
                                 'upstream_commit': 'a'*40, 'recipe_files': {'scripts/archive.py': 'b'*64}}}
        self.fingerprint = 'c'*64
        self.release = {'id': 123, 'draft': False, 'prerelease': True, 'tag_name': 'wsx-omarchy-4.0.6-r1'}
        self.manifest = manifest()
        self.manifest.update(distribution_id='wsx-omarchy', image_version='4.0.6-r1')
        self.build['build_identity'] = self.manifest['build_identity']
        self.marker = {'schema_version': 1, 'build_identity': self.manifest['build_identity'], 'assets': {}}
        self.sources = {'build_inputs': self.build, 'compression': {'verification_mode': 'full', 'passed': True,
                        'recipe_fingerprint': self.fingerprint, 'verified': list(policy.REQUIRED)}}
        self.contents = {'manifest.json': json.dumps(self.manifest).encode(), 'sources.json': json.dumps(self.sources).encode()}
        for name in asset_names(self.manifest):
            if name not in self.contents:
                self.contents[name] = b'fixture'
            raw = self.contents[name]
            self.marker['assets'][name] = {'size': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        self.manifest['compressed_size'] = self.marker['assets'][self.manifest['asset_name']]['size']
        self.manifest['sha256'] = self.marker['assets'][self.manifest['asset_name']]['sha256']
        self.contents['manifest.json'] = json.dumps(self.manifest).encode()
        self.marker['assets']['manifest.json'] = {'size': len(self.contents['manifest.json']), 'sha256': hashlib.sha256(self.contents['manifest.json']).hexdigest()}
        self.contents['completion.json'] = json.dumps(self.marker).encode()
        self.assets = [dict(id=name, name=name, size=len(raw), digest='sha256:'+hashlib.sha256(raw).hexdigest(), state='uploaded') for name,raw in self.contents.items()]

    def choose(self):
        def api(path):
            return {'private': True} if path == 'repos/'+policy.REPOSITORY else self.assets
        def download(repo, item, path):
            path.write_bytes(self.contents[item['name']])
        with patch.object(policy, 'fingerprint', return_value=self.fingerprint), patch.object(policy, 'releases', return_value=[self.release]), patch.object(policy, 'api', side_effect=api), patch.object(policy, 'download', side_effect=download):
            return policy.select(policy.REPOSITORY, self.build)

    def test_full_evidence_allows_stream_and_records_origin(self):
        result = self.choose()
        self.assertEqual(result['mode'], 'stream')
        self.assertEqual(result['evidence']['release_id'], self.release['id'])

    def test_draft_or_bad_digest_requires_full(self):
        self.release['draft'] = True
        self.assertEqual(self.choose()['mode'], 'full')
        self.release['draft'] = False
        next(x for x in self.assets if x['name'] == 'sources.json')['digest'] = 'sha256:'+'0'*64
        self.assertEqual(self.choose()['mode'], 'full')

    def test_stream_evidence_does_not_chain(self):
        data = copy.deepcopy(self.sources)
        data['compression']['verification_mode'] = 'stream'
        raw = json.dumps(data).encode()
        self.contents['sources.json'] = raw
        self.marker['assets']['sources.json'] = {'size': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        self.contents['completion.json'] = json.dumps(self.marker).encode()
        for item in self.assets:
            raw = self.contents[item['name']]
            item.update(size=len(raw), digest='sha256:'+hashlib.sha256(raw).hexdigest())
        self.assertEqual(self.choose()['mode'], 'full')

    def test_no_prior_release_or_api_failure_requires_full(self):
        with patch.object(policy, 'fingerprint', return_value=self.fingerprint), patch.object(policy, 'api', side_effect=OSError('offline')):
            self.assertEqual(policy.select(policy.REPOSITORY, self.build)['mode'], 'full')

    def test_recipe_and_tool_changes_change_fingerprint(self):
        with patch.object(policy.subprocess, 'check_output', side_effect=['tar 1\n', 'zstd 1\n']):
            first = policy.fingerprint(self.build)
        changed = copy.deepcopy(self.build)
        changed['inputs']['recipe_files']['scripts/archive.py'] = 'd'*64
        with patch.object(policy.subprocess, 'check_output', side_effect=['tar 1\n', 'zstd 1\n']):
            second = policy.fingerprint(changed)
        with patch.object(policy.subprocess, 'check_output', side_effect=['tar 2\n', 'zstd 1\n']):
            third = policy.fingerprint(self.build)
        self.assertEqual(len({first, second, third}), 3)
