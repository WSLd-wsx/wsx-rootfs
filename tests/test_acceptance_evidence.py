# SPDX-License-Identifier: GPL-2.0-or-later
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from acceptance_evidence import STAGES, validate_evidence
from test_contract import manifest

class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.manifest=manifest()
        self.evidence={'schema_version':1,'tag':'wsx-omarchy-4.0.6-r1','archive_sha256':'b'*64,
                       'manifest_sha256':'a'*64,'observed_at_utc':'2026-11-07T12:00:00Z',
                       'environment':{'windows_version':'Windows','wsl_version':'2','gpu_description':'GPU','graphics_runtime':'runtime'},
                       'stages':{key:{'result':'passed','source':'manual'} for key in STAGES}}
    def test_exact_manual_evidence(self):
        self.assertEqual(validate_evidence(self.evidence,self.manifest),self.evidence)
    def test_wrong_identity_and_untrusted_stages_rejected(self):
        changes=[('archive_sha256','c'*64),('tag','wsx-omarchy-4.0.6-r2'),('schema_version',True)]
        for field,value in changes:
            candidate=copy.deepcopy(self.evidence);candidate[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):validate_evidence(candidate,self.manifest)
        candidate=copy.deepcopy(self.evidence);candidate['stages']['gpu_first_frame']['source']='automatic'
        with self.assertRaises(ValueError):validate_evidence(candidate,self.manifest)
        candidate=copy.deepcopy(self.evidence);del candidate['stages']['normal_stop']
        with self.assertRaises(ValueError):validate_evidence(candidate,self.manifest)

    def test_cli_hashes_real_bytes_and_rejects_changed_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp); image=directory/'image'; image.write_bytes(b'fixture image')
            candidate=copy.deepcopy(self.manifest)
            candidate['sha256']=hashlib.sha256(image.read_bytes()).hexdigest()
            candidate['compressed_size']=image.stat().st_size
            manifest_path=directory/'manifest.json';manifest_path.write_text(json.dumps(candidate))
            evidence=copy.deepcopy(self.evidence)
            evidence['archive_sha256']=candidate['sha256']
            evidence['manifest_sha256']=hashlib.sha256(manifest_path.read_bytes()).hexdigest()
            evidence_path=directory/'evidence.json';evidence_path.write_text(json.dumps(evidence))
            command=[sys.executable,str(Path(__file__).resolve().parents[1]/'scripts/acceptance_evidence.py'),
                     '--evidence',str(evidence_path),'--manifest',str(manifest_path),'--archive',str(image),'--require-passed']
            self.assertEqual(subprocess.run(command,capture_output=True).returncode,0)
            image.write_bytes(b'wrong image!!')
            self.assertNotEqual(subprocess.run(command,capture_output=True).returncode,0)
