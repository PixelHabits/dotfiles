#!/usr/bin/env python3
"""Run the claude launcher against a fake binary in temporary git layouts."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1]
LAUNCHER = SOURCE / 'dot_local/bin/executable_claude'
FAKE = '#!/bin/sh\nprintf "%s\\n" "${CLAUDE_CODE_PROJECT_DIR_NAME-unset}" "$@"\n'
GIT = ['git', '-c', 'user.email=test@example.invalid', '-c', 'user.name=test']


class LauncherTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='claude-launcher-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.shim_dir = self.root / 'shim'
        self.real_dir = self.root / 'real'
        for directory in [self.shim_dir, self.real_dir]:
            directory.mkdir()
        shutil.copy(LAUNCHER, self.shim_dir / 'claude')
        (self.real_dir / 'claude').write_text(FAKE)
        for path in [self.shim_dir / 'claude', self.real_dir / 'claude']:
            path.chmod(0o755)
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        subprocess.run(['git', 'init', '-q', str(self.repo)], check=True)
        subprocess.run([*GIT, '-C', str(self.repo), 'commit', '-q', '--allow-empty', '-m', 'init'], check=True)

    def launch(self, cwd, *args, config_dir='/tmp/claude-config', preset=None, shim_first=True):
        dirs = [self.shim_dir, self.real_dir] if shim_first else [self.real_dir, self.shim_dir]
        env = {'PATH': os.pathsep.join([*map(str, dirs), os.environ['PATH']]), 'HOME': str(self.root)}
        if config_dir:
            env['CLAUDE_CONFIG_DIR'] = config_dir
        if preset:
            env['CLAUDE_CODE_PROJECT_DIR_NAME'] = preset
        result = subprocess.run(['claude', *args], cwd=cwd, env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        name, *argv = result.stdout.splitlines()
        return name, argv

    def test_bare_container_worktree_names_the_container(self):
        container = self.root / 'container'
        subprocess.run(['git', 'clone', '-q', '--bare', str(self.repo), str(container / '.bare')], check=True)
        subprocess.run(['git', '--git-dir', str(container / '.bare'), 'worktree', 'add', '-q', '--detach',
                        str(container / 'main')], check=True, capture_output=True)
        (container / 'main/sub').mkdir()
        self.assertEqual(self.launch(container / 'main', '--resume', 'x'), ('container', ['--resume', 'x']))
        self.assertEqual(self.launch(container / 'main/sub'), ('container', []))

    def test_nested_worktree_names_the_checkout(self):
        nested = self.repo / '.worktrees/feature'
        subprocess.run(['git', '-C', str(self.repo), 'worktree', 'add', '-q', '-b', 'feature', str(nested)],
                       check=True, capture_output=True)
        self.assertEqual(self.launch(nested), ('repo', []))

    def test_plain_clone_names_the_checkout(self):
        (self.repo / 'sub').mkdir()
        self.assertEqual(self.launch(self.repo), ('repo', []))
        self.assertEqual(self.launch(self.repo / 'sub'), ('repo', []))

    def test_container_root_uses_the_bare_directory(self):
        container = self.root / 'container'
        subprocess.run(['git', 'clone', '-q', '--bare', str(self.repo), str(container / '.bare')], check=True)
        self.assertEqual(self.launch(container), ('container', []))

    def test_non_git_directory_sets_nothing(self):
        plain = self.root / 'plain'
        plain.mkdir()
        self.assertEqual(self.launch(plain, 'arg'), ('unset', ['arg']))

    def test_explicit_name_wins(self):
        self.assertEqual(self.launch(self.repo, preset='chosen'), ('chosen', []))

    def test_no_config_dir_means_no_export(self):
        self.assertEqual(self.launch(self.repo, config_dir=None), ('unset', []))

    def test_real_binary_found_whatever_the_path_order(self):
        self.assertEqual(self.launch(self.repo, '-p', 'hi', shim_first=True), ('repo', ['-p', 'hi']))
        self.assertEqual(self.launch(self.repo, '-p', 'hi', shim_first=False), ('unset', ['-p', 'hi']))

    def test_missing_real_binary_fails_loudly(self):
        env = {'PATH': str(self.shim_dir), 'HOME': str(self.root)}
        result = subprocess.run(['claude'], cwd=self.repo, env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 127)
        self.assertIn('no other claude binary', result.stderr)


if __name__ == '__main__':
    unittest.main()
