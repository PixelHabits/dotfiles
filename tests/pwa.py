#!/usr/bin/env python3
"""Render PWA variants and exercise the launcher without touching the desktop."""

import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tempfile
import tomllib
from hyprland_tools import capture, native_verify


ROOT = Path(__file__).resolve().parents[1]
HOME = Path.home()


def run(args, **kwargs):
    result = subprocess.run(args, text=True, capture_output=True, **kwargs)
    if result.returncode:
        raise AssertionError(f'{shlex.join(args)}\n{result.stdout}\n{result.stderr}')
    return result.stdout


def jsonc(text):
    # Preserve strings while removing comments and JSONC trailing commas.
    text = re.sub(r'("(?:\\.|[^"\\])*")|//[^\n]*', lambda match: match[1] or '', text)
    text = re.sub(r'("(?:\\.|[^"\\])*")|,\s*([}\]])',
                  lambda match: match[1] or match[2], text)
    return json.loads(text)


def render_tests(temp):
    config = temp / 'chezmoi.toml'
    config.write_text('''[data]
email = "test@example.invalid"
hostname = "test-host"
osid = "arch"
desktop = "hyprland"
form_factor = "desktop"
profile = "work"
dev = true
''')
    base = ['chezmoi', '--config', str(config), '--source', str(ROOT),
            '--persistent-state', str(temp / 'state.db'), '--cache', str(temp / 'cache')]

    def cm(data, *args):
        return run(base + ['--override-data', json.dumps(data), *args])

    cases = [
        ({'profile': 'work'}, 'outlook.office.com', 'greenway-automotive'),
        ({'profile': 'personal'}, 'mail.google.com', ''),
        ({'profile': 'work', 'mail_provider': 'gmail',
          'linear_url': 'https://linear.app/another-workspace'}, 'mail.google.com', 'another-workspace'),
        ({'profile': 'personal', 'mail_provider': 'outlook'}, 'outlook.office.com', ''),
    ]
    for data, mail_host, workspace in cases:
        pwa = cm(data, 'cat', str(HOME / '.config/hypr/pwa.lua'))
        hypr = cm(data, 'cat', str(HOME / '.config/hypr/hyprland.lua'))
        bar = jsonc(cm(data, 'cat', str(HOME / '.config/waybar/config.jsonc')))
        captured = capture(temp, hypr, pwa)
        bindings = [binding for binding in captured['binds']
                    if binding['action']['name'] == 'hl.dsp.exec_cmd'
                    and binding['action']['args'][0].startswith('hypr-workspace-app ')]
        rules = {rule.get('workspace', ''): rule for rule in captured['rules'] if 'workspace' in rule}
        icons = bar['hyprland/workspaces']['format-icons']
        assert len(bindings) == 5
        assert set(rules) == {'name:' + app for app in ['chat', 'mail', 'music', 'linear', 'teams']}
        assert icons['linear'] == '◩' and 'notion' not in icons
        for binding in bindings:
            argv = shlex.split(binding['action']['args'][0])
            app, pattern = argv[1:3]
            assert app in icons
            assert rules['name:' + app]['match']['class'] == pattern
            host = mail_host if app == 'mail' else {
                'chat': 't3.chat', 'music': 'music.youtube.com',
                'linear': 'linear.app', 'teams': 'teams.microsoft.com',
            }[app]
            for profile in ['Default', 'Profile 2']:
                assert re.fullmatch(pattern, f'chrome-{host}__some_path-{profile}'), (pattern, host)
            assert not re.fullmatch(pattern, f'chrome-{host}.evil__-Default')
            assert not re.fullmatch(pattern, 'helium-browser')
            if app == 'mail':
                assert mail_host in argv[-1]
            if app == 'linear':
                assert argv[-1] == '--app=https://linear.app' + (f'/{workspace}' if workspace else '')
        all_keys = [binding['keys'] for binding in captured['binds']]
        assert len(set(all_keys)) == len(all_keys), 'Duplicate shortcut'
        lock = next(binding for binding in captured['binds'] if binding['keys'] == 'SUPER + L')
        assert lock['action']['args'] == ['loginctl lock-session']
        assert 'require("pwa")(mainMod, browser)' in hypr
        if data['profile'] == 'personal':
            assert 'greenway' not in pwa
        native_verify(temp)

    for os_name in ['linux', 'darwin']:
        paths = cm({'desktop': 'none', 'chezmoi': {'os': os_name}}, 'managed').splitlines()
        assert not any(path.startswith(('.config/hypr/', '.config/waybar/')) or
                       path == '.local/bin/hypr-workspace-app' for path in paths)

    for data in [{'mail_provider': 'unknown'}, {'linear_url': 'https://evil.example'},
                 {'linear_url': 'https://linear.app/ok\nbind = bad'}]:
        result = subprocess.run(base + ['--override-data', json.dumps(data), 'cat',
                                       str(HOME / '.config/hypr/pwa.lua')], capture_output=True, text=True)
        assert result.returncode != 0
        assert 'mail_provider' in result.stderr or 'linear_url' in result.stderr

    # Simulate fresh initialization prompts, then preserve explicit choices on re-init.
    template = (ROOT / '.chezmoi.toml.tmpl').read_text()
    result = run(base + ['execute-template', '--init', '--promptChoice', 'Mail provider=gmail',
                        '--promptString', 'Linear landing URL=https://linear.app/custom'], input=template)
    parsed = tomllib.loads(result)
    assert parsed['sourceDir'] == str(ROOT)
    assert parsed['data']['mail_provider'] == 'gmail'
    assert parsed['data']['linear_url'] == 'https://linear.app/custom'
    config.write_text(result)
    run(base + ['init'])
    assert tomllib.loads(config.read_text()) == parsed
    print('PASS: provider/profile rendering, matching, shortcuts, icons, gating, invalid input, and init persistence')


def launcher_tests(temp):
    bin_dir = temp / 'bin'
    bin_dir.mkdir()
    stub = bin_dir / 'hyprctl'
    stub.write_text('''#!/usr/bin/env python3
import json, os, sys
with open(os.environ['CALLS'], 'a') as log:
    log.write(json.dumps(sys.argv[1:]) + '\\n')
if sys.argv[1] in ('monitors', 'clients'):
    print(os.environ[sys.argv[1].upper()])
''')
    stub.chmod(0o755)
    launch = bin_dir / 'launch'
    launch.write_text('#!/usr/bin/env python3\nimport os\nopen(os.environ["LAUNCHED"], "w").write("yes")\n')
    launch.chmod(0o755)
    client = {'workspace': {'name': 'mail'}, 'class': 'chrome-mail.google.com__mail_u_0_-Profile 2'}
    for i, (visible, clients, expected_launch) in enumerate([
        (True, [client], False), (False, [client], False), (False, [], True),
        (True, [{'workspace': {'name': 'mail'}, 'class': 'other-app'}], True),
    ]):
        calls, launched = temp / f'calls-{i}', temp / f'launch-{i}'
        env = dict(os.environ, PATH=str(bin_dir) + os.pathsep + os.environ['PATH'],
                   CALLS=str(calls), LAUNCHED=str(launched), CLIENTS=json.dumps(clients),
                   MONITORS=json.dumps([{'name': 'DP-1', 'activeWorkspace': {'name': 'mail' if visible else '1'}}]))
        run(['bash', str(ROOT / 'dot_local/bin/executable_hypr-workspace-app'),
             'mail', '^chrome-mail[.]google[.]com__.*$', str(launch)], env=env)
        operations = [json.loads(line) for line in calls.read_text().splitlines()]
        expected_focus = ['dispatch', 'focusmonitor', 'DP-1'] if visible else [
            'dispatch', 'focusworkspaceoncurrentmonitor', 'name:mail']
        assert expected_focus in operations
        assert launched.exists() == expected_launch
    print('PASS: launcher focuses visible/hidden workspaces and opens only when the matching app is absent')


if __name__ == '__main__':
    for command in ['chezmoi', 'bash', 'jq']:
        if not shutil.which(command):
            raise SystemExit(f'Missing required command: {command}')
    with tempfile.TemporaryDirectory(prefix='pwa-tests-') as directory:
        temp = Path(directory)
        render_tests(temp)
        launcher_tests(temp)
    if not shutil.which('Hyprland'):
        print('SKIP: native Hyprland parsing (Hyprland is not installed)')
