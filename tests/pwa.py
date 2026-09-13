#!/usr/bin/env python3
"""Render the PWA templates and check the generated hyprland/waybar/pwa output."""

import json
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
HOME = Path.home()
EXPECTED_APPS = {'chat', 'mail', 'music', 'linear', 'teams'}


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


if __name__ == '__main__':
    if not shutil.which('chezmoi'):
        raise SystemExit('Missing required command: chezmoi')
    for test in [test_hyprland_machine, test_non_hyprland_machine]:
        with tempfile.TemporaryDirectory(prefix='pwa-tests-') as directory:
            test(Path(directory))
    if not shutil.which('Hyprland'):
        print('SKIP: native Hyprland parsing (Hyprland is not installed)')
