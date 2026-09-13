#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.14"
# dependencies = []
# ///
"""Render the PWA templates and check the generated hyprland/waybar/pwa output."""

import json
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tempfile
import tomllib


ROOT = Path(__file__).resolve().parents[1]
HOME = Path.home()
EXPECTED_APPS = {'chat', 'mail', 'music', 'linear', 'teams', 'github'}


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


def render(temp, data):
    config = temp / 'chezmoi.toml'
    config.write_text('''[data]
email = "test@example.invalid"
hostname = "test-host"
osid = "arch"
desktop = "hyprland"
form_factor = "laptop"
profile = "work"
dev = true
''')
    return ['chezmoi', '--config', str(config), '--source', str(ROOT),
            '--persistent-state', str(temp / 'state.db'), '--cache', str(temp / 'cache'),
            '--override-data', json.dumps(data)]


def test_hyprland_machine(temp):
    base = render(temp, {})
    pwa = run(base + ['cat', str(HOME / '.config/hypr/pwa.conf')])
    hypr = run(base + ['cat', str(HOME / '.config/hypr/hyprland.conf')])
    bar = jsonc(run(base + ['cat', str(HOME / '.config/waybar/config.jsonc')]))

    bindings = [line for line in pwa.splitlines() if line.startswith('bindd =')]
    assert len(bindings) == len(EXPECTED_APPS)
    assert set(re.findall(r'workspace = name:(\w+)', pwa)) == EXPECTED_APPS
    assert EXPECTED_APPS <= bar['hyprland/workspaces']['format-icons'].keys()
    assert 'bindd = $mainMod, L, Lock session' in hypr
    assert 'SHIFT, N, Vim' in hypr and 'SHIFT, V, Vim' not in hypr
    assert f'source = {HOME}/.config/hypr/pwa.conf' in hypr

    if shutil.which('Hyprland'):
        rendered = temp / 'pwa.conf'
        rendered.write_text('$mainMod = SUPER\n$browser = helium-browser\n' + pwa)
        output = run(['Hyprland', '--verify-config', '--config', str(rendered)], cwd=temp)
        assert 'config ok' in output, output
    print('PASS: laptop/hyprland machine renders pwa.conf, hyprland.conf, and waybar with all apps')


def test_non_hyprland_machine(temp):
    base = render(temp, {'desktop': 'none'})
    paths = run(base + ['managed']).splitlines()
    assert not any(path.startswith(('.config/hypr/', '.config/waybar/')) or
                   path == '.local/bin/hypr-workspace-app' for path in paths)
    print('PASS: non-hyprland machine manages no hyprland or waybar files')


def test_provider_choices(temp):
    data = {'ai_provider': 'claude', 'mail_provider': 'proton', 'music_provider': 'apple',
            'chat_provider': 'slack', 'project_provider': 'notion', 'project_url': 'https://www.notion.so',
            'github_url': 'https://github.com/example-org'}
    base = render(temp, data)
    apps = json.loads(run(base + ['execute-template', '{{ includeTemplate "pwa-apps.json.tmpl" . }}']))
    by_id = {app['workspace']: app for app in apps}
    assert by_id['chat']['url'] == 'https://claude.ai'
    assert by_id['mail']['host'] == 'mail.proton.me'
    assert by_id['music']['host'] == 'music.apple.com'
    assert by_id['teams']['host'] == 'app.slack.com'
    assert by_id['github']['url'] == data['github_url']
    for app in apps:
        assert re.fullmatch(app['class'], f"chrome-{app['host']}__some_path-Profile 2")
        assert not re.fullmatch(app['class'], f"chrome-{app['host']}.evil__-Default")
    config = run(base + ['execute-template', '--init', '--file', str(ROOT / '.chezmoi.toml.tmpl')])
    saved = tomllib.loads(config)['data']
    assert all(saved[key] == value for key, value in data.items())
    for bad in [{'ai_provider': 'unknown'}, {'github_url': 'https://evil.example'},
                {'project_url': 'https://linear.app/work\nbind = bad'}]:
        result = subprocess.run(render(temp, bad) + ['cat', str(HOME / '.config/hypr/pwa.conf')], capture_output=True)
        assert result.returncode != 0
    fresh = run(render(temp, {}) + ['execute-template', '--init', '--file', str(ROOT / '.chezmoi.toml.tmpl'),
        '--promptChoice', 'AI Chat provider=chatgpt,Music provider=apple,Messages provider=discord,Projects provider=notion',
        '--promptString', 'Projects landing URL=https://www.notion.so,GitHub landing URL=https://github.com/example-org'])
    answers = tomllib.loads(fresh)['data']
    assert answers['ai_provider'] == 'chatgpt' and answers['project_provider'] == 'notion'
    assert answers['github_url'] == 'https://github.com/example-org'
    assert 'greenway'  not in (ROOT / '.chezmoidata/pwa.toml').read_text().lower()
    print('PASS: provider choices, host matching, saved initialization answers, and invalid URLs')


if __name__ == '__main__':
    if not shutil.which('chezmoi'):
        raise SystemExit('Missing required command: chezmoi')
    for test in [test_hyprland_machine, test_non_hyprland_machine, test_provider_choices]:
        with tempfile.TemporaryDirectory(prefix='pwa-tests-') as directory:
            test(Path(directory))
    if not shutil.which('Hyprland'):
        print('SKIP: native Hyprland parsing (Hyprland is not installed)')
