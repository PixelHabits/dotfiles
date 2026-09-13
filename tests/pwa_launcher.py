#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.14"
# dependencies = []
# ///
"""Exercise launcher failure paths without connecting to Hyprland."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='pwa-launcher-') as directory:
    temp = Path(directory)
    fake = temp / 'hyprctl'
    fake.write_text(f'#!{sys.executable}\n' + '''import os, sys
command = sys.argv[1]
if command == 'monitors': print('[]')
elif command == 'dispatch': print(os.environ.get('FOCUS_REPLY', 'ok'))
elif command == 'clients':
    print(os.environ['CLIENTS'])
    sys.exit(int(os.environ.get('CLIENTS_EXIT', '0')))
''')
    fake.chmod(0o755)
    marker = temp / 'launched'
    for name, clients, extra, success, launch in [
        ('absent', '[]', {}, True, True),
        ('present', json.dumps([{'workspace': {'name': 'mail'}, 'class': 'chrome-mail'}]), {}, True, False),
        ('bad JSON', '{', {}, False, False),
        ('failed query', '[]', {'CLIENTS_EXIT': '1'}, False, False),
        ('failed focus', '[]', {'FOCUS_REPLY': 'error'}, False, False),
    ]:
        marker.unlink(missing_ok=True)
        env = dict(os.environ, PATH=f'{temp}:{os.environ["PATH"]}', CLIENTS=clients, **extra)
        result = subprocess.run(['bash', str(ROOT / 'dot_local/bin/executable_hypr-workspace-app'),
            'mail', '^chrome-mail$', 'touch', str(marker)], env=env, capture_output=True)
        assert (result.returncode == 0) == success, name
        assert marker.exists() == launch, name
print('PASS: existing/absent app, invalid clients, failed query, and failed focus')
