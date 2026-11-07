"""Inventory coverage and pending deletion evidence without modifying the repo."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('license_audit',ROOT/'scripts/audit-licenses.py')
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)


class LicenseInventoryTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name)
        for name,data in {
            'docs/provenance.json':{'files':[]},
            'components/cachyos-provenance.json':{'files':[]},
            'distros/cachyos-plasma/upstream/source.json':{'files':{},'iso_identity':{'files':{}}},
            'docs/licensing/rules.json':{'rules':[dict(id='fixture',priority=1,paths=['kept.txt'],group='conditional-future-license',basis='fixture',limitation='fixture',next_step='fixture')]},
        }.items():
            p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data))
        (self.root/'kept.txt').write_text('source')
        self.names='kept.txt\0removed.txt\0'
        def git(*args):
            if args[:2]==('ls-files','-co'):return self.names
            if args[:2]==('ls-files','-d'):return 'removed.txt\0'
            if args[0]=='log':return ''
            if args[0]=='rev-parse':return 'a'*40
            raise AssertionError(args)
        for mock in (patch.object(audit,'ROOT',self.root),patch.object(audit,'git',git)):
            mock.start();self.addCleanup(mock.stop)

    def test_tracked_removal_is_visible_without_losing_current_coverage(self):
        result=audit.inventory()
        self.assertEqual(result['removed_tracked_paths'],['removed.txt'])
        self.assertEqual([f['path'] for f in result['files']],['kept.txt'])
        self.assertFalse(result['release_ready'])

    def test_uncovered_new_path_is_rejected(self):
        self.names+='new.txt\0';(self.root/'new.txt').write_text('new')
        with self.assertRaisesRegex(ValueError,'Uncovered path'):
            audit.inventory()

    def test_dangling_link_is_not_treated_as_a_deleted_file(self):
        (self.root/'removed.txt').symlink_to(self.root/'missing')
        with self.assertRaisesRegex(ValueError,'Unsupported inventory entry'):
            audit.inventory()
