#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.14"
# dependencies = []
# ///
"""Exercise the references templates in disposable homes without touching the real home."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1]
SETTINGS = SOURCE / 'dot_config/claude/modify_private_settings.json'
CODEX_HOOKS = SOURCE / 'dot_config/codex/hooks.json'
MANIFEST = SOURCE / 'dot_agents/references.json'
BUILD_SCRIPT = SOURCE / 'run_onchange_after_agent-references.sh.tmpl'
REFS = '~/.local/bin/refs hook claude'
EVENTS = {'SessionStart', 'UserPromptSubmit', 'PostToolUse'}


class ReferencesTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='references-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / 'home'
        self.home.mkdir()
        for directory in ['.config', '.local/share']:
            (self.home / directory).mkdir(parents=True)
        self.config = self.root / 'chezmoi.toml'
        self.configure()
        self.env = {
            'PATH': os.environ['PATH'], 'HOME': str(self.home),
            'XDG_CONFIG_HOME': str(self.home / '.config'),
            'XDG_DATA_HOME': str(self.home / '.local/share'),
            'XDG_STATE_HOME': str(self.home / '.local/state'),
        }

    def configure(self, dev=True, agent_home_managed=False):
        self.config.write_text(
            '[data]\n' + f'dev = {str(dev).lower()}\nprofile = "work"\n'
            'desktop = "none"\nform_factor = "server"\nhostname = "test"\n'
            'osid = "ubuntu"\nemail = "test@example.invalid"\n'
            f'agent_home_managed = {str(agent_home_managed).lower()}\n'
        )

    def chezmoi(self, *args, stdin=None, check=True):
        return subprocess.run(
            ['chezmoi', '--config', str(self.config), '--source', str(SOURCE),
             '--destination', str(self.home), '--persistent-state', str(self.root / 'state.db'),
             *args], input=stdin, env=self.env, cwd=self.root,
            capture_output=True, text=True, check=check, timeout=30,
        )

    def render_settings(self, existing):
        return json.loads(self.chezmoi('execute-template', '--with-stdin', SETTINGS.read_text(), stdin=existing).stdout)

    def refs_hooks(self, settings, event):
        return [entry for entry in settings['hooks'][event]
                if any(hook['command'].startswith(REFS) for hook in entry['hooks'])]

    def test_settings_add_hooks_and_keep_existing_entries(self):
        local = {
            'model': 'local-model',
            'hooks': {
                'SessionStart': [{'matcher': 'startup', 'hooks': [{'type': 'command', 'command': 'echo other'}]}],
                'Stop': [{'hooks': [{'type': 'command', 'command': 'echo stop'}]}],
            },
        }
        settings = self.render_settings(json.dumps(local))
        self.assertEqual(settings['model'], 'local-model')
        self.assertEqual(settings['hooks']['Stop'], local['hooks']['Stop'])
        self.assertEqual(settings['hooks']['SessionStart'][0], local['hooks']['SessionStart'][0])
        for event in EVENTS:
            with self.subTest(event=event):
                ours = self.refs_hooks(settings, event)
                self.assertEqual(len(ours), 1)
                self.assertEqual(ours[0]['hooks'][0]['command'], f'{REFS} {event}')
        self.assertEqual(settings['hooks']['SessionStart'][1]['matcher'], 'startup|resume|clear|compact')
        self.assertEqual(settings['hooks']['PostToolUse'][0]['matcher'], 'Bash')
        self.assertNotIn('matcher', settings['hooks']['UserPromptSubmit'][0])

    def test_settings_render_is_idempotent_and_replaces_old_refs_entries(self):
        first = self.chezmoi('execute-template', '--with-stdin', SETTINGS.read_text(), stdin='{}').stdout
        second = self.chezmoi('execute-template', '--with-stdin', SETTINGS.read_text(), stdin=first).stdout
        self.assertEqual(first, second)
        stale = json.loads(first)
        stale['hooks']['SessionStart'][0]['hooks'][0]['command'] = f'{REFS} SessionStart --old-flag'
        settings = self.render_settings(json.dumps(stale))
        self.assertEqual(len(self.refs_hooks(settings, 'SessionStart')), 1)
        self.assertEqual(settings['hooks']['SessionStart'][0]['hooks'][0]['command'], f'{REFS} SessionStart')

    def test_codex_hooks_file_shape(self):
        hooks = json.loads(CODEX_HOOKS.read_text())['hooks']
        self.assertEqual(set(hooks), EVENTS)
        for event, entries in hooks.items():
            with self.subTest(event=event):
                self.assertEqual(len(entries), 1)
                hook = entries[0]['hooks'][0]
                self.assertEqual(hook['type'], 'command')
                self.assertEqual(hook['command'], f'~/.local/bin/refs hook codex {event}')
                self.assertGreater(hook['additionalContextLimit'], 2500)
        self.assertEqual(hooks['SessionStart'][0]['matcher'], 'startup|resume|clear|compact')
        self.assertEqual(hooks['PostToolUse'][0]['matcher'], 'Bash')

    def test_manifest_is_a_valid_alias_record(self):
        manifest = json.loads(MANIFEST.read_text())
        self.assertTrue(manifest)
        for alias, entry in manifest.items():
            with self.subTest(alias=alias):
                self.assertRegex(alias, r'^[a-z0-9][a-z0-9._-]*$')
                self.assertRegex(entry['repository'], r'^[\w.-]+/[\w.-]+$')
                self.assertEqual(set(entry) - {'repository', 'ref', 'description', 'depth'}, set())

    def test_dev_gating(self):
        expected = ['.agents/references.json', '.agents/skills/references/SKILL.md',
                    '.local/share/agent-references/src/cli.ts', '.config/codex/hooks.json']
        for dev in [True, False]:
            with self.subTest(dev=dev):
                self.configure(dev=dev)
                managed = self.chezmoi('managed', '--include', 'files').stdout.splitlines()
                scripts = self.chezmoi('managed', '--include', 'scripts').stdout.splitlines()
                for path in expected:
                    self.assertEqual(path in managed, dev, path)
                self.assertEqual('agent-references.sh' in scripts, dev)

    def test_managed_agent_home_keeps_the_tool_but_not_the_codex_hooks(self):
        self.configure(agent_home_managed=True)
        managed = self.chezmoi('managed', '--include', 'files').stdout.splitlines()
        self.assertIn('.local/share/agent-references/src/cli.ts', managed)
        self.assertIn('.agents/references.json', managed)
        self.assertNotIn('.config/codex/hooks.json', managed)
        self.assertNotIn('.config/claude/settings.json', managed)

    def test_build_script_hashes_every_source_file(self):
        script = self.chezmoi('execute-template', '--file', str(BUILD_SCRIPT)).stdout
        for source in sorted((SOURCE / 'dot_local/share/agent-references/src').glob('*.ts')):
            self.assertIn(f'# {source.name} hash: ', script)
        self.assertIn('# package.json hash: ', script)
        self.assertIn('# bun.lock hash: ', script)
        self.assertIn('bun install --cwd', script)
        self.assertIn(f'source={self.home}/.local/share/agent-references', script)
        self.assertIn(f'target={self.home}/.local/bin/refs', script)
        subprocess.run(['sh', '-n'], input=script, text=True, check=True)

    def test_apply_places_the_manifest_and_hooks_without_running_scripts(self):
        targets = [str(self.home / target) for target in ['.agents', '.config/codex', '.local/share/agent-references']]
        self.chezmoi('apply', '--exclude', 'scripts', *targets)
        manifest = json.loads((self.home / '.agents/references.json').read_text())
        self.assertIn('effect-ts', manifest)
        hooks = json.loads((self.home / '.config/codex/hooks.json').read_text())['hooks']
        self.assertEqual(set(hooks), EVENTS)
        self.assertTrue((self.home / '.local/share/agent-references/src/cli.ts').exists())
        self.assertFalse((self.home / '.local/bin/refs').exists())


if __name__ == '__main__':
    unittest.main()
