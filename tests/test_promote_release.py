# SPDX-License-Identifier: GPL-2.0-or-later
import importlib.util
import hashlib
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('promote_release', ROOT / 'scripts/promote-release.py')
promotion = importlib.util.module_from_spec(spec)
spec.loader.exec_module(promotion)


class PromotionTests(unittest.TestCase):
    tag = 'WSX-omarchy-4.5.0-r3'

    def test_tag_only_review_derives_hashes_and_requires_explicit_attestation(self):
        manifest_bytes = b'{"candidate": true}'
        archive_sha = 'b' * 64
        manifest_sha = hashlib.sha256(manifest_bytes).hexdigest()
        snapshot = {'source_commit': 'a' * 40}

        def download(command, **kwargs):
            (Path(command[-1]) / 'manifest.json').write_bytes(manifest_bytes)

        with patch.object(promotion, 'release_snapshot', return_value=(snapshot, 'c' * 64)), \
             patch.object(promotion.subprocess, 'run', side_effect=download), \
             patch.object(promotion, 'stable_manifest', return_value={
                 'sha256': archive_sha, 'minimum_wsx_core_version': '0.2.3',
             }):
            report = promotion.review(self.tag, None, None, 'maintainer')
            hashes = {'archive_sha256': archive_sha, 'manifest_sha256': manifest_sha}
            self.assertEqual(report['verified_asset_hashes'], hashes)
            self.assertNotIn('manual_attestation', report)

            report = promotion.review(self.tag, None, None, 'maintainer', hardware_accepted=True)
            self.assertEqual(report['manual_attestation']['attested_by'], 'maintainer')
            for key, value in hashes.items():
                self.assertEqual(report['manual_attestation'][key], value)

            with self.assertRaisesRegex(ValueError, 'Acceptance hashes do not match'):
                promotion.review(self.tag, archive_sha, 'd' * 64, 'maintainer')

    def test_snapshot_changes_when_tag_moves(self):
        commit = {'type': 'commit', 'sha': 'a' * 40}
        responses = [
            {'full_name': promotion.REPO, 'private': False},
            {'tag_name': self.tag, 'id': 7, 'draft': False, 'prerelease': True},
            [{'id': 3, 'name': 'manifest.json', 'size': 1, 'state': 'uploaded', 'digest': 'sha256:' + 'b' * 64}],
            {'object': commit},
        ]
        with patch.object(promotion, 'api', side_effect=responses):
            _, first = promotion.release_snapshot(self.tag)
        commit['sha'] = 'c' * 40
        with patch.object(promotion, 'api', side_effect=responses):
            _, second = promotion.release_snapshot(self.tag)
        self.assertNotEqual(first, second)

    def test_changed_snapshot_stops_before_mutation(self):
        with patch.object(promotion, 'release_snapshot', return_value=({'release_id': 7}, 'b' * 64)), \
             patch.object(promotion.subprocess, 'run') as call:
            with self.assertRaisesRegex(ValueError, 'differs from the verified snapshot'):
                promotion.promote(self.tag, 'a' * 64)
            call.assert_not_called()

    def test_verified_snapshot_updates_only_prerelease(self):
        published = {'tag_name': self.tag, 'draft': False, 'prerelease': False}
        with patch.object(promotion, 'release_snapshot', return_value=({'release_id': 7}, 'a' * 64)), \
             patch.object(promotion, 'api', return_value=published) as api, \
             patch.object(promotion.subprocess, 'run') as call:
            promotion.promote(self.tag, 'a' * 64)
            path = f'repos/{promotion.REPO}/releases/7'
            self.assertEqual(call.call_args.args[0], ['gh', 'api', '--method', 'PATCH', path, '-F', 'prerelease=false'])
            api.assert_called_once_with(path)
