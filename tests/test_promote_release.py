# SPDX-License-Identifier: GPL-2.0-or-later
import importlib.util
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

    def test_missing_independent_review_stops_before_mutation(self):
        environment = {'protection_rules': [
            {'type': 'required_reviewers', 'prevent_self_review': False, 'reviewers': [{}]},
        ]}
        with patch.object(promotion, 'api', return_value=environment), patch.object(promotion.subprocess, 'run') as call:
            with self.assertRaisesRegex(ValueError, 'prevent self-review'):
                promotion.promote(self.tag, 'a' * 64)
            call.assert_not_called()

    def test_changed_snapshot_stops_before_mutation(self):
        with patch.object(promotion, 'require_approval_configuration'), \
             patch.object(promotion, 'release_snapshot', return_value=({'release_id': 7}, 'b' * 64)), \
             patch.object(promotion.subprocess, 'run') as call:
            with self.assertRaisesRegex(ValueError, 'differs from the approved snapshot'):
                promotion.promote(self.tag, 'a' * 64)
            call.assert_not_called()

    def test_approved_snapshot_updates_only_prerelease(self):
        published = {'tag_name': self.tag, 'draft': False, 'prerelease': False}
        with patch.object(promotion, 'require_approval_configuration'), \
             patch.object(promotion, 'release_snapshot', return_value=({'release_id': 7}, 'a' * 64)), \
             patch.object(promotion, 'api', return_value=published) as api, \
             patch.object(promotion.subprocess, 'run') as call:
            promotion.promote(self.tag, 'a' * 64)
            path = f'repos/{promotion.REPO}/releases/7'
            self.assertEqual(call.call_args.args[0], ['gh', 'api', '--method', 'PATCH', path, '-F', 'prerelease=false'])
            api.assert_called_once_with(path)
