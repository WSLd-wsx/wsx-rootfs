# SPDX-License-Identifier: GPL-2.0-or-later OR Apache-2.0
"""A fresh source repository must not silently select retired releases."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import shared_sources


class FreshRepository(unittest.TestCase):
    def test_default_inputs_are_unselected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'components').mkdir()
            (root/'components/source-delivery.json').write_text(json.dumps({
                'schema_version': 1, 'mode': 'shared-v2',
                'profiles': {'omarchy': None, 'cachyos-plasma': None},
            }))
            for profile in ('omarchy', 'cachyos-plasma'):
                with self.assertRaisesRegex(ValueError, 'No publicly available shared source pin'):
                    shared_sources.pin_for(root, profile)


if __name__ == '__main__':
    unittest.main()
