#!/usr/bin/env python3
"""Compare native Lua declarations with the committed pre-migration bindings."""
import json
from pathlib import Path
import subprocess
import tempfile
from hyprland_tools import capture, native_verify

ROOT = Path(__file__).resolve().parents[1]
DIRECTIONS = dict(l='left', r='right', u='up', d='down')


def expected_action(binding):
    name, arg = binding['legacy_dispatcher'], binding['legacy_arg']
    no_args = dict(killactive='window.close', pseudo='window.pseudo', pin='window.pin', movewindow='window.drag', resizewindow='window.resize')
    if name in no_args:
        return {'name': 'hl.dsp.' + no_args[name], 'args': {}}
    names = dict(exec='exec_cmd', layoutmsg='layout', togglespecialworkspace='workspace.toggle_special')
    value = arg
    if name == 'sendshortcut':
        names[name] = 'send_shortcut'
        value = dict(zip(['mods', 'key', 'window'], map(str.strip, arg.split(','))))
    elif name == 'togglefloating':
        names[name], value = 'window.float', {'action': 'toggle'}
    elif name == 'fullscreen':
        names[name], value = 'window.fullscreen', {'mode': 'maximized' if arg == '1' else 'fullscreen'}
    elif name in ['movefocus', 'swapwindow']:
        names[name], value = ('focus' if name == 'movefocus' else 'window.swap'), {'direction': DIRECTIONS[arg]}
    elif name == 'workspace':
        names[name], value = 'focus', {'workspace': int(arg) if arg.isdigit() else arg}
    elif name in ['movetoworkspace', 'movetoworkspacesilent']:
        names[name], value = 'window.move', {'workspace': int(arg) if arg.isdigit() else arg, 'follow': name == 'movetoworkspace'}
    elif name == 'resizeactive':
        x, y = map(int, arg.split())
        names[name], value = 'window.resize', dict(x=x, y=y, relative=True)
    elif name == 'movecurrentworkspacetomonitor':
        names[name], value = 'workspace.move', {'monitor': arg}
    return {'name': 'hl.dsp.' + names[name], 'args': [value]}


with tempfile.TemporaryDirectory(prefix='hypr-lua-') as directory:
    temp = Path(directory)
    config = temp / 'chezmoi.toml'
    config.write_text('[data]\nhostname="GAM-DEV001"\nprofile="work"\ndesktop="hyprland"\n')
    base = ['chezmoi', '--config', str(config), '--source', str(ROOT), 'execute-template', '--file']
    hypr, pwa = [subprocess.check_output(base + [str(ROOT / f'dot_config/hypr/{name}.lua.tmpl')], text=True) for name in ['hyprland', 'pwa']]
    calls = capture(temp, hypr, pwa)
    native_verify(temp)
    by_key = {binding['keys']: binding for binding in calls['binds']}
    assert len(by_key) == len(calls['binds']), 'Duplicate key bindings'
    baseline = json.loads((ROOT / 'tests/hyprland-v1-bindings.json').read_text())
    assert len(calls['binds']) == len(baseline) + 5
    for binding in baseline:
        actual = by_key[binding['keys']]
        assert actual['flags'] == binding['options'], (binding, actual)
        assert actual['action'] == expected_action(binding), (binding, actual)
    assert calls['startup'] == ["uwsm app -- ghostty -e zsh -c 'tmux attach || tmux new -s main'", 'uwsm app -- hyprlauncher -d']
    assert calls['env'] == {'XCURSOR_SIZE': '24', 'HYPRCURSOR_SIZE': '24'}
    assert calls['gesture'] == dict(fingers=3, direction='horizontal', action='workspace')
    assert calls['device'] == dict(name='epic-mouse-v1', sensitivity=-0.5)
    assert len(calls['monitors']) == 6
    assert calls['monitors'][1] == dict(output='desc:Samsung Display Corp. ATNA60KA02', mode='3200x2000@120.00', position='auto-center-down', scale=1.25, vrr=1, bitdepth=10, cm='dcip3')
    assert calls['config'][0]['general']['gaps_in'] == 0
    assert calls['config'][0]['general']['border_size'] == 1
    assert calls['config'][0]['animations']['enabled'] is False
    assert len(calls['curves']) == 5 and len(calls['animations']) == 17
    rules = {rule['name']: rule for rule in calls['rules']}
    assert len(rules) == 10
    assert rules['fix-xwayland-drags'] == {'name': 'fix-xwayland-drags', 'match': {'class': '^$', 'title': '^$', 'xwayland': True, 'float': True, 'fullscreen': False, 'pin': False}, 'no_focus': True}
    assert rules['move-hyprland-run']['move'] == '20 monitor_h-120'
    for app in ['localsend', '1password']:
        assert rules['float-' + app]['float'] and rules['float-' + app]['center']
    assert calls['layers'] == [{'name': 'selection-no-animation', 'match': {'namespace': 'selection'}, 'no_anim': True}]
    print(f"PASS: {len(baseline)} legacy bindings, five PWA bindings, flags, startup, monitor data, and rules")

# Preserve Unicode, literal escape sequences, quotes, and newlines through chezmoi/Lua.
for value in ['display\u00a0name', 'literal \\u0041', 'line\nnext', '"; error("injection") --', 'quote\\" and 日本語']:
    encoded = subprocess.check_output(['chezmoi', '--source', str(ROOT), '--override-data', json.dumps({'sample': value}),
                                       'execute-template', '{{ includeTemplate "lua-value" .sample }}'], text=True)
    decoded = subprocess.check_output(['lua', '-e', 'io.write(' + encoded + ')'], text=True)
    assert decoded == value, (value, encoded, decoded)
print('PASS: Lua value encoding preserves Unicode and literal escapes')

# Reject the old monitor shape with a useful error instead of emitting broken Lua.
invalid = subprocess.run(['chezmoi', '--source', str(ROOT), '--override-data',
                          json.dumps({'hyprland': {'monitors': [', preferred, auto, 1']}}),
                          'execute-template', '--file', str(ROOT / 'dot_config/hypr/hyprland.lua.tmpl')],
                         capture_output=True, text=True)
assert invalid.returncode != 0 and 'must contain tables' in invalid.stderr
print('PASS: old comma-separated monitor overrides fail with conversion guidance')
