import json
from pathlib import Path
import unittest
import jsonschema
from test_contract import manifest


class SchemaTests(unittest.TestCase):
    def test_desktop_protocol_is_explicit_and_closed(self):
        schema = json.loads((Path(__file__).resolve().parents[1]/'schema/manifest-v1.schema.json').read_text())
        candidate = manifest()
        candidate['desktop_compatibility'] = dict(schema_version=1,lifecycle_abi=1,display_abi=1,
            sharing_path='opaque-v1',producer_abi=1,consumer_abi=2,retirement='guest-stop-v1',
            guest_protocol_major=1,guest_protocol_minor=0,runtime_receipt_sha256='a'*64,
            guest_profile_sha256='b'*64,required_capabilities=['account.status'])
        jsonschema.validate(candidate, schema)
        for key,value in [('guest_protocol_major',2),('guest_profile_sha256','invalid'),('unknown_required',True)]:
            bad = json.loads(json.dumps(candidate)); bad['desktop_compatibility'][key] = value
            with self.assertRaises(jsonschema.ValidationError): jsonschema.validate(bad, schema)

    def test_schema_and_example(self):
        schema = json.loads((Path(__file__).resolve().parents[1]/'schema/manifest-v1.schema.json').read_text())
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.validate(manifest(), schema)
        candidate = manifest(); candidate['minimum_wsx_core_version'] = None
        candidate['guest_interface_abi'] = None
        jsonschema.validate(candidate, schema)
        candidate['source_delivery_schema'] = 1
        jsonschema.validate(candidate, schema)
        candidate['source_delivery_schema'] = 2
        jsonschema.validate(candidate, schema)
        candidate['source_delivery_schema'] = 3
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(candidate, schema)
        candidate['source_delivery_schema'] = 1
        candidate['compressed_size'] = True
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(candidate, schema)

    def test_cachyos_cpu_requirement_schema(self):
        schema = json.loads((Path(__file__).resolve().parents[1]/'schema/manifest-v1.schema.json').read_text())
        candidate = manifest('2026.11.1-r1', 'wsx-cachyos-plasma')
        candidate['cpu_requirements'] = {'architecture_level': 'x86-64-v3'}
        jsonschema.validate(candidate, schema)
        candidate['cpu_requirements']['architecture_level'] = 'unknown'
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(candidate, schema)
