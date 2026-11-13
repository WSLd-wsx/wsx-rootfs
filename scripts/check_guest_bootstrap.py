# Original WSX code, PolyForm-Noncommercial-1.0.0. See LICENSE-MAP.md.
"""Check the packaged v2 bootstrap without claiming desktop activation."""
import json
import subprocess


def check(root):
    request = dict(protocol='wsx-guest-bootstrap', major=2, id='offline-v2',
                   operation='capabilities', params={})
    result = subprocess.run(['chroot', str(root), '/usr/bin/python3', '-I',
                             '/usr/lib/wsx/bootstrap-v2.py'],
                            input=json.dumps(request), capture_output=True,
                            text=True, check=True, timeout=15)
    reply = json.loads(result.stdout)
    if (reply.get('protocol') != request['protocol'] or reply.get('major') != 2
            or reply.get('id') != request['id'] or reply.get('ok') is not True
            or reply.get('result', {}).get('activation_supported') is not False):
        raise ValueError('Packaged Guest v2 bootstrap capability check failed')
    return reply
