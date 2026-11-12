#!/usr/bin/env python3
"""Stage the paired private runtime and a parameterized prototype desktop entry."""
# Generator logic: GPL-2.0-or-later; source-expression exceptions below.
# Expression exceptions (also apply to these portions in source form):
# Owner-original strings/replacements inserted into desktop.py are MIT.
# Original session installer adaptations remain GPL-2.0-or-later.
# See docs/licensing/OUTPUT-LICENSES.md and licenses/WSX-MIT.txt.
import argparse
import ast
import hashlib
import json
from pathlib import Path
import shutil
import runpy
import subprocess

ROOT=Path(__file__).resolve().parents[1]


def hashes(path):
    result={}
    for p in sorted(path.rglob('*')):
        if p.is_file():
            with p.open('rb') as stream:
                result[str(p.relative_to(path))]=hashlib.file_digest(stream,'sha256').hexdigest()
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('rootfs',type=Path);p.add_argument('components',type=Path);args=p.parse_args()
    root=args.rootfs.resolve();runtime=root/'usr/lib/wsx/runtime';runtime.mkdir(parents=True)
    for name in ('mesa','venus'):
        shutil.copytree(args.components/name,runtime/name,symlinks=True)
    consumer=runtime/'opaque-consumer'
    shutil.copytree(args.components/'opaque-consumer', consumer, symlinks=True)
    for folder in ('session','network'):
        shutil.copytree(ROOT/'vendor/wsx-proto'/folder,runtime/folder)
    runpy.run_path(str(ROOT/'scripts/session_venus_policy.py'))['configure'](runtime/'session')
    # Parameterize the reference session installer; retain its ownership checks.
    installer=runtime/'session/install.py'
    text=installer.read_text().replace("account = pwd.getpwnam('omarchy')", "account = pwd.getpwnam(os.environ['WSX_USER'])")
    installer.write_text(text)
    source=(ROOT/'vendor/wsx-proto/device-host/production/start-guest.py').read_text()
    tree=ast.parse(source); lines=source.splitlines(keepends=True)
    names={'run','mesa_environment','prepare_x11_directory','desktop'}
    parts=[]
    for node in tree.body:
        if isinstance(node,(ast.Import,ast.ImportFrom)) or isinstance(node,ast.FunctionDef) and node.name in names:
            parts.append(''.join(lines[node.lineno-1:node.end_lineno]))
    # AST extraction omits comments, including the original license notice.
    header=''.join(lines[:tree.body[0].lineno-1])
    text=header + '# Adapted by the WSX rootfs staging recipe from vendor/wsx-proto/device-host/production/start-guest.py.\nimport runpy\n' + '\n'.join(parts)
    text=runpy.run_path(str(ROOT/'scripts/graphics_debug.py'))['configure'](text)
    replacements={
      "LANG='C.UTF-8'":"LANG=os.environ['WSX_LOCALE']",
      "env.update(private_mesa)":"env.update(private_mesa)\n    if profile.get('pulse_server'):\n        env['PULSE_SERVER'] = profile['pulse_server']",
      "account = pwd.getpwnam('omarchy')":"account = pwd.getpwnam(os.environ['WSX_USER'])",
      "profile = json.loads((deployment.parent / 'wsx-runtime.json').read_text())":"profile = json.loads((Path('/run/wsx') / (instance.hex + '.json')).read_text())",
      "if consumer.exists():":"if os.environ['WSX_SHARING_PATH'] == 'opaque-v1' and consumer.exists():",
      "if metadata.get('opaque_import'):":"if os.environ['WSX_SHARING_PATH'] == 'opaque-v1' and metadata.get('opaque_import'):",
      "    if manifest.get('linear_modifier_feedback'):":"    if os.environ['WSX_SHARING_PATH'] == 'linear-v1' and not manifest.get('linear_modifier_feedback'):\n        raise RuntimeError('Missing paired LINEAR modifier support')\n    if manifest.get('linear_modifier_feedback'):",
    }
    for old,new in replacements.items():
        if text.count(old)!=1: raise ValueError('Unexpected prototype entry: '+old)
        text=text.replace(old,new)
    old="    run(['/usr/bin/udevadm', 'settle', '--timeout=5'])"
    if text.count(old)!=1:raise ValueError('Unexpected input readiness path')
    text=text.replace(old,old+"\n    runpy.run_path('/usr/lib/wsx/device-view.py')['prepare_input'](instance)")
    # Install was completed during user initialization; avoid relying on a
    # hard-coded account in a subprocess with an isolated Python environment.
    old="run(['/usr/bin/python3', '-I', str(deployment / 'session/install.py'), account.pw_dir])"
    if text.count(old)!=1:raise ValueError('Unexpected session adapter call')
    text=text.replace(old,"assert (Path(account.pw_dir) / '.local/bin/wsx-launch-app').is_file()")
    # Both negotiated paths use the pinned compositor. Only the explicit
    # opaque branch may enable its descriptor protocol or private kernel ABI.
    old = '    return env'
    if text.count(old) != 1:
        raise ValueError('Unexpected graphics environment return')
    common = """    bundle = json.loads((consumer / 'manifest.json').read_text())
    if bundle.get('abi') != 2 or not {'bin/Hyprland', 'lib/libaquamarine.so.14'}.issubset(bundle.get('files', {})):
        raise RuntimeError('Incomplete pinned compositor bundle')
    for relative, expected in bundle['files'].items():
        path = (consumer / relative).resolve(strict=True)
        if not path.is_relative_to(consumer):
            raise RuntimeError('Compositor file escapes its bundle')
        with path.open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != expected:
                raise RuntimeError('Compositor hash mismatch: ' + relative)
    env['WSX_COMPOSITOR_EXECUTABLE'] = str(consumer / 'bin/Hyprland')
    env['LD_LIBRARY_PATH'] = str(consumer / 'lib') + ':' + str(prefix / 'lib')
    return env"""
    text = text.replace(old, common)
    text = text.replace("    return env", "    env['VN_PERF'] = 'no_async_mem_alloc' if os.environ['WSX_SHARING_PATH'] == 'linear-v1' else ''\n    return env", 1)
    old = "private_mesa.get('WSX_OPAQUE_COMPOSITOR_EXECUTABLE', '/usr/bin/Hyprland')"
    if text.count(old) != 1:
        raise ValueError('Unexpected compositor selection')
    text = text.replace(old, "private_mesa['WSX_COMPOSITOR_EXECUTABLE']")
    text+='\nif __name__ == "__main__":\n    desktop(sys.argv[1], uuid.UUID(sys.argv[2]))\n'
    (runtime/'desktop.py').write_text(text)
    subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror',
                    '-I'+str(ROOT/'vendor/rvgpu/include'),str(ROOT/'guest/input.c'),
                    '-o',str(runtime/'wsx-input-guest')],check=True)
    for source,target in [('guest/wsx-guest.py','usr/bin/wsx-guest'),('guest/initialize-user.sh','usr/lib/wsx/initialize-user.sh')]:
        shutil.copy2(ROOT/source,root/target);(root/target).chmod(0o755)
    (root/'usr/lib/wsx/runtime-files.json').write_text(json.dumps(hashes(runtime),indent=2)+'\n')

    runpy.run_path(str(ROOT/'scripts/stage-protocol.py'))['stage'](root, 'hyprland')


if __name__=='__main__': main()
