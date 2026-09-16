#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.14"
# dependencies = []
# ///
"""Exercise Claude configuration in disposable homes without starting an agent."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1]
SETTINGS = SOURCE / 'dot_config/claude/modify_private_settings.json'


class ClaudeConfigTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='claude-config-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / 'home'
        self.home.mkdir()
        for directory in ['.config/zsh/zshenv.d', '.local/bin', '.local/state']:
            (self.home / directory).mkdir(parents=True)
        self.config = self.root / 'chezmoi.toml'
        self.configure()
        self.env = {
            'PATH': os.environ['PATH'], 'HOME': str(self.home),
            'XDG_CONFIG_HOME': str(self.home / '.config'),
            'XDG_CACHE_HOME': str(self.home / '.cache'),
            'XDG_DATA_HOME': str(self.home / '.local/share'),
            'XDG_STATE_HOME': str(self.home / '.local/state'),
        }

    def configure(self, dev=True, profile='work'):
        self.config.write_text(
            '[data]\n' + f'dev = {str(dev).lower()}\nprofile = "{profile}"\n'
            'desktop = "none"\nform_factor = "server"\nhostname = "test"\n'
            'osid = "ubuntu"\nemail = "test@example.invalid"\n'
        )

    def chezmoi(self, *args, stdin=None, check=True):
        return subprocess.run(
            ['chezmoi', '--config', str(self.config), '--source', str(SOURCE),
             '--destination', str(self.home), '--persistent-state', str(self.root / 'state.db'),
             *args], input=stdin, env=self.env, cwd=self.root,
            capture_output=True, text=True, check=check, timeout=30,
        )

    def render_settings(self, existing):
        return self.chezmoi('execute-template', '--with-stdin', SETTINGS.read_text(), stdin=existing)

    def test_modify_template_preserves_native_keys_and_enforces_managed(self):
        local = {
            'model': 'local-model', 'permissions': {'defaultMode': 'auto', 'deny': ['Read(secret)']},
            'enabledPlugins': {'local-plugin': True}, 'env': {'DO_NOT_TRACK': '1'},
            'statusLine': {'type': 'command', 'command': 'echo local'},
            'attribution': {'other': 'keep'},
        }
        first = self.render_settings(json.dumps(local)).stdout
        result = json.loads(first)
        for key in ['model', 'enabledPlugins', 'statusLine']:
            self.assertEqual(result[key], local[key])
        self.assertEqual(result['env'], local['env'] | {'CLAUDE_BASH_MAINTAIN_PROJECT_WORKING_DIR': '1'})
        self.assertEqual(result['permissions'], local['permissions'] | {'deny': ['Read(secret)', 'EnterWorktree']})
        self.assertEqual(result['attribution'], {'commit': '', 'pr': '', 'sessionUrl': False, 'other': 'keep'})
        self.assertEqual(first, self.render_settings(first).stdout)

        fresh = json.loads(self.render_settings('').stdout)
        self.assertEqual(fresh['permissions'], {'deny': ['EnterWorktree']})
        self.assertEqual(fresh['env'], {'CLAUDE_BASH_MAINTAIN_PROJECT_WORKING_DIR': '1'})

    def test_actual_apply_uses_modify_template_and_preserves_invalid_input(self):
        target = self.home / '.config/claude/settings.json'
        target.parent.mkdir(parents=True)
        target.write_text(json.dumps({'model': 'local-model', 'statusLine': {'type': 'command', 'command': 'echo local'}}))
        self.chezmoi('apply', '--exclude', 'scripts', str(target))
        first = target.read_text()
        self.assertEqual(json.loads(first)['statusLine'], {'type': 'command', 'command': 'echo local'})
        self.assertEqual(json.loads(first)['attribution']['commit'], '')
        self.assertEqual(json.loads(first)['model'], 'local-model')
        self.assertEqual(target.stat().st_mode & 0o777, 0o600)
        self.chezmoi('apply', '--exclude', 'scripts', str(target))
        self.assertEqual(target.read_text(), first)
        target.write_text('{invalid')
        self.assertNotEqual(self.chezmoi('apply', '--exclude', 'scripts', str(target), check=False).returncode, 0)
        self.assertEqual(target.read_text(), '{invalid')

    def test_working_dir_env_and_worktree_deny_merge_once(self):
        local = {
            'env': {'DO_NOT_TRACK': '1', 'EDITOR': 'nvim'},
            'permissions': {'defaultMode': 'auto', 'allow': ['Bash(ls *)'], 'deny': ['Read(secret)']},
        }
        first = self.render_settings(json.dumps(local)).stdout
        result = json.loads(first)
        self.assertEqual(result['env'], local['env'] | {'CLAUDE_BASH_MAINTAIN_PROJECT_WORKING_DIR': '1'})
        self.assertEqual(result['permissions'], local['permissions'] | {'deny': ['Read(secret)', 'EnterWorktree']})
        self.assertEqual(first, self.render_settings(first).stdout)
        self.assertEqual(json.loads(self.render_settings(first).stdout)['permissions']['deny'].count('EnterWorktree'), 1)
        preset = json.loads(self.render_settings(json.dumps({'permissions': {'deny': ['EnterWorktree']}})).stdout)
        self.assertEqual(preset['permissions'], {'deny': ['EnterWorktree']})

    def test_symlink_templates_render_shared_paths(self):
        for name in ['CLAUDE.md', 'settings.json']:
            template = (SOURCE / f'dot_local/state/private_claude/symlink_{name}.tmpl').read_text()
            rendered = self.chezmoi('execute-template', template).stdout.strip()
            self.assertEqual(rendered, str(self.home / '.config/claude' / name))

    def test_non_dev_gating(self):
        claude_paths = ['.config/claude/CLAUDE.md', '.config/claude/settings.json',
                         '.local/state/claude/settings.json', '.config/zsh/zshenv.d/21-claude.zsh', '.local/bin/claude']

        self.configure(dev=False)
        managed = self.chezmoi('managed').stdout.splitlines()
        for path in claude_paths:
            self.assertNotIn(path, managed)
        self.assertNotIn('claude.md', managed)
        self.assertFalse(any(path.startswith('tests/') for path in managed))

    def test_zsh_redirects_and_overrides(self):
        template = (SOURCE / 'dot_config/zsh/zshenv.d/21-claude.zsh.tmpl').read_text()
        shell = self.chezmoi('execute-template', template).stdout
        script = self.root / 'redirect.zsh'
        script.write_text(shell + '\nprint -r -- "$CLAUDE_CONFIG_DIR|$CLAUDE_CODE_TMPDIR|$TMPDIR|$DO_NOT_TRACK"\n')
        env = self.env | {'TMPDIR': '/unchanged', 'DO_NOT_TRACK': '1'}
        result = subprocess.check_output(['zsh', '-f', str(script)], env=env, text=True)
        self.assertEqual(result.strip(), f'{self.home}/.local/state/claude|{self.home}/.local/state/claude/tmp|/unchanged|1')
        env |= {'CLAUDE_CONFIG_DIR': '/custom/runtime', 'CLAUDE_CODE_TMPDIR': '/custom/scratch'}
        result = subprocess.check_output(['zsh', '-f', str(script)], env=env, text=True)
        self.assertEqual(result.strip(), '/custom/runtime|/custom/scratch|/unchanged|1')

    def test_native_plugin_writes_preserve_settings_symlink(self):
        claude = shutil.which('claude')
        if not claude:
            self.skipTest('Claude Code is not installed')
        self.chezmoi('apply', '--exclude', 'scripts',
                     str(self.home / '.config/claude'), str(self.home / '.local/state/claude'))
        marketplace = self.root / 'marketplace'
        (marketplace / '.claude-plugin').mkdir(parents=True)
        plugin = marketplace / 'plugins/fixture/.claude-plugin'
        plugin.mkdir(parents=True)
        (marketplace / '.claude-plugin/marketplace.json').write_text(json.dumps({
            'name': 'fixture', 'owner': {'name': 'Fixture'},
            'plugins': [{'name': 'fixture', 'source': './plugins/fixture'}],
        }))
        (plugin / 'plugin.json').write_text(json.dumps({'name': 'fixture', 'version': '1.0.0'}))
        env = self.env | {
            'CLAUDE_CONFIG_DIR': str(self.home / '.local/state/claude'),
            'CLAUDE_CODE_TMPDIR': str(self.home / '.local/state/claude/tmp'),
            'DO_NOT_TRACK': '1', 'DISABLE_AUTOUPDATER': '1',
            'ANTHROPIC_BASE_URL': 'http://127.0.0.1:9',
        }
        for args in [['plugin', 'marketplace', 'add', str(marketplace)],
                     ['plugin', 'install', 'fixture@fixture']]:
            subprocess.run([claude, *args], cwd=self.root, env=env, check=True,
                           text=True, capture_output=True, timeout=30)
        runtime = self.home / '.local/state/claude/settings.json'
        self.assertTrue(runtime.is_symlink())
        settings = json.loads((self.home / '.config/claude/settings.json').read_text())
        self.assertTrue(settings['enabledPlugins']['fixture@fixture'])
        self.assertEqual(settings['attribution']['commit'], '')
        self.chezmoi('apply', '--exclude', 'scripts', str(self.home / '.config/claude/settings.json'))
        self.assertEqual(json.loads(runtime.read_text()), settings)


if __name__ == '__main__':
    unittest.main()
