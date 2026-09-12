#!/usr/bin/env python3
"""Capture shell IPC in mocks, then validate dispatcher construction natively."""
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import tempfile
from hyprland_tools import native_verify

ROOT = Path(__file__).resolve().parents[1]
expressions, rules = [], []
with tempfile.TemporaryDirectory(prefix='hypr-ipc-') as directory:
    temp = Path(directory)
    binary = temp / 'hyprctl'
    binary.write_text('''#!/usr/bin/env python3
import json, os, sys
with open(os.environ['CALLS'], 'a') as log: log.write(json.dumps(sys.argv[1:]) + '\\n')
queries = {'activewindow': 'WINDOW', 'clients': 'CLIENTS', 'activeworkspace': 'WORKSPACE'}
print(os.environ[queries[sys.argv[1]]] if sys.argv[1] in queries else os.environ.get('REPLY', 'ok'))
''')
    binary.chmod(0o755)
    notify = temp / 'notify-send'
    notify.write_text('#!/bin/sh\nexit 0\n')
    notify.chmod(0o755)

    def helper(name, args=(), window=None, clients=None, workspace=None, reply='ok'):
        log = temp / 'calls'
        log.write_text('')
        env = os.environ | dict(PATH=f'{temp}:/usr/bin:/bin', CALLS=str(log),
                                 WINDOW=json.dumps(window or {}), CLIENTS=json.dumps(clients or []),
                                 WORKSPACE=json.dumps(workspace or {'id': 4, 'tiledLayout': 'dwindle'}), REPLY=reply)
        result = subprocess.run(['bash', str(ROOT / 'dot_local/bin' / ('executable_' + name)), *args], env=env, text=True, capture_output=True)
        calls = [json.loads(line) for line in log.read_text().splitlines()]
        for call in calls:
            if call[0] == 'dispatch':
                assert len(call) == 2 and call[1].startswith('hl.dsp.'), call
                expressions.append(call[1])
            elif call[0] == 'eval':
                rules.append(call[1])
        return result, calls

    for pinned, expected in [(False, 6), (True, 3)]:
        result, calls = helper('omarchy-hyprland-window-pop', window={'address': '0x123', 'pinned': pinned})
        assert result.returncode == 0, result.stderr
        assert len([call for call in calls if call[0] == 'dispatch']) == expected
        assert all('address:0x123' in call[1] for call in calls if call[0] == 'dispatch')
    result, calls = helper('omarchy-hyprland-window-pop', ['800', '600', '-10', '20'], window={'address': '0x123', 'pinned': False})
    assert result.returncode == 0
    assert any('x = -10, y = 20, relative = true' in call[1] for call in calls if call[0] == 'dispatch')
    result, calls = helper('omarchy-hyprland-window-pop')
    assert result.returncode == 0 and len(calls) == 1
    result, calls = helper('omarchy-hyprland-window-pop', ['1); error("bad")'])
    assert result.returncode != 0 and calls == []
    result, calls = helper('omarchy-hyprland-window-pop', window={'address': 'not-an-address'})
    assert result.returncode != 0 and len(calls) == 1
    result, calls = helper('omarchy-hyprland-window-pop', window={'address': '0x123'}, reply='error: rejected')
    assert result.returncode != 0 and len(calls) == 2
    for clients in [[], [{'address': '0x123'}, {'address': '0xabc'}]]:
        result, calls = helper('omarchy-hyprland-window-close-all', clients=clients)
        assert result.returncode == 0, result.stderr
        assert len(calls) == len(clients) + 2
        assert calls[-1] == ['dispatch', 'hl.dsp.focus({ workspace = 1 })']
    result, calls = helper('omarchy-hyprland-window-close-all', clients=[{'address': 'bad"'}])
    assert result.returncode != 0 and len(calls) == 1
    for current, target in [('dwindle', 'scrolling'), ('scrolling', 'dwindle')]:
        result, calls = helper('omarchy-hyprland-workspace-layout-toggle', workspace={'id': 4, 'tiledLayout': current})
        assert result.returncode == 0, result.stderr
        assert calls[-1] == ['eval', f'hl.workspace_rule({{ workspace = "4", layout = "{target}" }})']

    result, calls = helper('omarchy-hyprland-workspace-layout-toggle', workspace={'id': -1337, 'name': 'mail', 'tiledLayout': 'dwindle'})
    assert result.returncode == 0, result.stderr
    assert calls[-1] == ['eval', 'hl.workspace_rule({ workspace = "name:mail", layout = "scrolling" })']

    # These constructs are parsed only; dispatcher functions are never invoked.
    expressions += ['hl.dsp.focus({ monitor = "DP-1" })', 'hl.dsp.focus({ workspace = "name:mail", on_current_monitor = true })']
    idle = (ROOT / 'dot_config/hypr/hypridle.conf').read_text()
    for command in re.findall(r"hyprctl dispatch '([^']+)'", idle):
        expressions.append(command)
    assert {'hl.dsp.dpms({ action = "on" })', 'hl.dsp.dpms({ action = "off" })'} <= set(expressions)
    bar = subprocess.check_output(['chezmoi', '--source', str(ROOT), 'execute-template', '--file', str(ROOT / 'dot_config/waybar/config.jsonc.tmpl')], text=True)
    for line in bar.splitlines():
        if '"on-scroll-' in line and 'hyprctl' in line:
            command = json.loads(line.strip().rstrip(',').split(':', 1)[1])
            expressions.append(shlex.split(command)[2])
    (temp / 'hyprland.lua').write_text('\n'.join('hl.bind("F1", ' + expression + ')' for expression in expressions) + '\n' + '\n'.join(rules))
    native_verify(temp)
print(f'PASS: shell helper branches, rejected input/errors, and {len(expressions)} native IPC dispatcher constructions')
