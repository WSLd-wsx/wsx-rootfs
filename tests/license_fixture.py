"""Small synthetic policy fixture; never evidence about real project rights."""
import json
from pathlib import Path


def seed(root):
    files = {
        'LICENSE': 'Fixture license mapping, not a real grant\n',
        'LICENSE-MAP.md': 'Fixture map\n',
        'docs/licensing/OUTPUT-LICENSES.md': 'Fixture output scope\n',
        'docs/licensing/PRIVATE-ARTIFACTS.md': 'Fixture private policy\n',
        'recipe.py': '# Fixture build recipe\n',
        'vendor/example.c': '/* Fixture original notice */\n',
        'docs/licensing/licenses/MIT.txt': 'Fixture reference text\n',
        'docs/licensing/modules.json': dict(license_grant=False,
            modules={'gpl-build-materials': dict(treatment='Fixture compatible candidate', proposed_license='GPL-2.0-or-later'),
                     'wsx-independent': dict(treatment='Fixture restricted candidate')},
            path_overrides={'restricted.py':'wsx-independent'}, rule_modules={'fixture':'gpl-build-materials'},
            license_selection={'effective':False}),
        'docs/licensing/rules.json': dict(rules=[dict(id='fixture',priority=0,paths=['*'],group='conditional-future-license')]),
        'docs/licensing/license-text-sources.json': dict(files=[]),
        'components/license-boundaries.json': dict(license_grant=False, roots={'fixture-rebuild':['recipe.py']},
            dependencies={}, installed_inputs={}, activation_blockers=['fixture, not legal acceptance'],
            outputs=[dict(id='fixture', profiles=['omarchy'], installed_paths=['usr/bin/fixture'],
                          source_paths=['vendor/example.c'], license_treatment='Fixture notice', kind='compiled')]),
    }
    for name, value in files.items():
        path = root/name; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value,indent=2)+'\n' if isinstance(value,dict) else value)
