"""License application metadata is a versioned build input, not a legal grant."""
from pathlib import Path

POLICY_FILES = (
    'LICENSE', 'LICENSE-MAP.md', 'docs/licensing/OUTPUT-LICENSES.md',
    'docs/licensing/PRIVATE-ARTIFACTS.md', 'docs/licensing/modules.json', 'docs/licensing/rules.json',
    'docs/licensing/license-text-sources.json', 'components/license-boundaries.json',
)


def paths(root):
    result = list(POLICY_FILES)
    result.extend(str(p.relative_to(root)) for p in sorted((root/'docs/licensing/licenses').rglob('*')) if p.is_file())
    for name in result:
        path = root/name
        if path.is_symlink() or not path.is_file():
            raise ValueError('Missing regular licensing input: ' + name)
    return sorted(set(result))
