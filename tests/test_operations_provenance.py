"""Build identities must bind the separate operations workflow when supplied."""
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from operations_provenance import attach
from contract import identity

class Provenance(unittest.TestCase):
    def test_optional_and_bound(self):
        original={'distribution_id':'wsx-omarchy'}
        self.assertEqual(attach(original,{}),original)
        updated=attach(original,dict(WSX_OPERATIONS_REPOSITORY='WSLd-wsx/wsx-rootfs-ops',
                                     WSX_OPERATIONS_COMMIT='a'*40))
        self.assertNotEqual(identity(original),identity(updated))
        self.assertEqual(updated['operations_commit'],'a'*40)
    def test_partial_untrusted_and_invalid_origin_rejected(self):
        for env in (dict(WSX_OPERATIONS_COMMIT='a'*40),
                    dict(WSX_OPERATIONS_REPOSITORY='other/repo',WSX_OPERATIONS_COMMIT='a'*40),
                    dict(WSX_OPERATIONS_REPOSITORY='WSLd-wsx/wsx-rootfs-ops',WSX_OPERATIONS_COMMIT='main')):
            with self.subTest(env=env), self.assertRaises(ValueError): attach({},env)
