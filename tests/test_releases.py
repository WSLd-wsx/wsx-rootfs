import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from releases import select


def release(tag, **flags):
    return dict(tag_name=tag, draft=False, prerelease=False) | flags


class SelectionTests(unittest.TestCase):
    def test_numeric_order_not_upload_order(self):
        self.assertEqual(select([release('v4.10.0'), release('v4.9.9')])['tag_name'], 'v4.10.0')

    def test_candidates_and_drafts_excluded(self):
        rows = [release('v9.0.0', draft=True), release('v8.0.0', prerelease=True),
                release('v7.0.0-rc1'), release('v6.0.0-beta'), release('v4.0.6')]
        self.assertEqual(select(rows)['tag_name'], 'v4.0.6')

    def test_explicit_missing_never_falls_back(self):
        with self.assertRaises(ValueError):
            select([release('v4.0.6')], '4.0.7')

    def test_missing_metadata_rejects(self):
        with self.assertRaises(ValueError):
            select([{'tag_name': 'v4.0.6'}])

    def test_explicit_draft_rejects(self):
        with self.assertRaises(ValueError):
            select([release('v4.0.6', draft=True)], '4.0.6')


if __name__ == '__main__':
    unittest.main()
