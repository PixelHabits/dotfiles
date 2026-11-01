#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.14"
# dependencies = []
# ///
"""Run the PWA provider prompts of `chezmoi init` against a temporary configuration."""
import json
from pathlib import Path
import subprocess
import tempfile
import tomllib

ROOT = Path(__file__).resolve().parents[1]


def init(temp, data, *prompts):
    config = temp / 'chezmoi.toml'
    config.write_text('[data]\nemail = "test@example.invalid"\ndesktop = "hyprland"\nform_factor = "laptop"\nprofile = "work"\ndev = true\n')
    return subprocess.run(
        ['chezmoi', '--config', str(config), '--source', str(ROOT), '--persistent-state', str(temp / 'state.db'),
         '--cache', str(temp / 'cache'), '--override-data', json.dumps(data),
         'execute-template', '--init', '--file', str(ROOT / '.chezmoi.toml.tmpl'), *prompts],
        stdin=subprocess.DEVNULL, capture_output=True, text=True)


with tempfile.TemporaryDirectory(prefix='pwa-tests-') as directory:
    temp = Path(directory)
    saved = {'ai_provider': 'claude', 'mail_provider': 'proton', 'music_provider': 'apple', 'chat_provider': 'slack',
             'project_provider': 'notion', 'project_url': 'https://www.notion.so', 'github_url': 'https://github.com/example-org'}
    result = init(temp, saved)
    assert result.returncode == 0, result.stderr
    data = tomllib.loads(result.stdout)['data']
    assert {key: data[key] for key in saved} == saved, data
    print('PASS: initialization keeps saved provider choices and landing URLs')

    result = init(temp, {},
                  '--promptChoice', 'AI Chat provider=chatgpt,Music provider=apple,Messages provider=discord,Projects provider=notion',
                  '--promptString', 'Projects landing URL=https://www.notion.so,GitHub landing URL=https://github.com/example-org')
    assert result.returncode == 0, result.stderr
    data = tomllib.loads(result.stdout)['data']
    assert data['ai_provider'] == 'chatgpt' and data['project_provider'] == 'notion' and data['mail_provider'] == 'gmail', data
    assert data['github_url'] == 'https://github.com/example-org', data
    print('PASS: a new machine saves its prompt answers')

    for bad in [{'ai_provider': 'unknown'}, {'github_url': 'https://evil.example'}, {'project_url': 'https://linear.app/work\nbind = bad'}]:
        assert init(temp, bad).returncode != 0, bad
    print('PASS: unknown providers and URLs off the provider domain are rejected')
