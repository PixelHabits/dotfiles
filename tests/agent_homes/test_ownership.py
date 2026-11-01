#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.14"
# dependencies = []
# ///
"""Test optional agent ownership with temporary homes and representative files."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import tomllib
import unittest

SOURCE = Path(__file__).resolve().parents[2]
DATA = ('[data]\ndev = true\ndesktop = "none"\nprofile = "personal"\nhostname = "fixture"\n'
        'email = "fixture@example.invalid"\nform_factor = "server"\nosid = "arch"\n')
AGENT_PATHS = (
    ".config/codex/config.toml", ".config/codex/AGENTS.md", ".config/codex/hooks.json",
    ".config/zsh/zshenv.d/20-codex.zsh",
    ".config/claude/settings.json", ".config/claude/CLAUDE.md",
    ".config/zsh/zshenv.d/21-claude.zsh", ".local/state/claude/settings.json",
    ".local/state/claude/CLAUDE.md", ".local/bin/claude",
)
SHARED_PATHS = (
    ".config/zsh/zshenv.d/06-xdg-apps.zsh", ".config/agents/AGENTS.md",
    ".agents/references.json", ".local/share/agent-references/src/cli.ts",
)


class AgentOwnershipTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="agent-ownership-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.home = self.root / "home with spaces"
        self.home.mkdir()
        self.source = self.root / "source"
        self.source.mkdir()
        for directory in (".chezmoidata", ".chezmoitemplates", "dot_config/codex",
                          "dot_config/environment.d", "dot_config/zsh"):
            shutil.copytree(SOURCE / directory, self.source / directory)
        for filename in (".chezmoi.toml.tmpl", ".chezmoiignore", "dot_zshenv"):
            shutil.copy2(SOURCE / filename, self.source / filename)
        # Related PRs supply these paths. The fixture keeps this test self-contained.
        for relative in (
            "dot_config/codex/AGENTS.md", "dot_config/codex/hooks.json",
            "dot_config/claude/settings.json", "dot_config/claude/CLAUDE.md",
            "dot_config/zsh/zshenv.d/21-claude.zsh",
            "dot_config/environment.d/20-claude.conf",
            "dot_local/state/private_claude/settings.json",
            "dot_local/state/private_claude/CLAUDE.md", "dot_local/bin/executable_claude",
            "dot_config/agents/AGENTS.md", "dot_agents/references.json",
            "dot_local/share/agent-references/src/cli.ts",
        ):
            target = self.source / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            candidates = (target, target.with_name(target.name + ".tmpl"),
                          target.with_name("symlink_" + target.name + ".tmpl"))
            if not any(path.exists() for path in candidates):
                target.write_text("fixture\n")
        self.config = self.root / "chezmoi.toml"
        self.configure()
        self.env = {"HOME": str(self.home), "PATH": os.environ["PATH"],
                    "CODEX_HOME": str(self.home / ".config/codex")}
        self.command = [shutil.which("chezmoi"), "--source", str(self.source),
                        "--destination", str(self.home), "--config", str(self.config),
                        "--persistent-state", str(self.root / "state.boltdb")]

    def configure(self, external=None):
        flag = "" if external is None else f"agent_home_managed = {str(external).lower()}\n"
        self.config.write_text(DATA + flag)

    def chezmoi(self, *args):
        return subprocess.check_output(self.command + list(args), env=self.env,
                                       cwd=self.home, text=True)

    def test_default_manages_the_agent_paths(self):
        managed = self.chezmoi("managed").splitlines()
        for path in AGENT_PATHS + SHARED_PATHS:
            self.assertIn(path, managed, path)

    def test_external_ownership_excludes_agents_and_keeps_shared_tools(self):
        self.configure(external=True)
        self.env["CODEX_HOME"] = str(self.root / "provider codex")
        managed = self.chezmoi("managed").splitlines()
        for path in AGENT_PATHS:
            self.assertNotIn(path, managed, path)
        for path in (".config/environment.d/20-claude.conf", ".config/environment.d/22-codex.conf"):
            self.assertNotIn(path, managed, path)
        for path in SHARED_PATHS:
            self.assertIn(path, managed, path)

    def test_apply_preserves_existing_agent_files(self):
        self.configure(external=True)
        self.env["CODEX_HOME"] = str(self.root / "provider codex")
        for relative in AGENT_PATHS:
            path = self.home / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("existing provider file\n")
        self.chezmoi("apply", "--exclude", "scripts")
        for relative in AGENT_PATHS:
            self.assertEqual((self.home / relative).read_text(), "existing provider file\n")
        for relative in SHARED_PATHS:
            self.assertTrue((self.home / relative).is_file(), relative)

    def test_init_preserves_an_explicit_choice_and_defaults_false(self):
        for choice in (None, True, False):
            self.configure(external=choice)
            rendered = self.chezmoi("execute-template", "--init", "--file",
                                    str(self.source / ".chezmoi.toml.tmpl"))
            self.assertEqual(tomllib.loads(rendered)["data"]["agent_home_managed"], bool(choice))


if __name__ == "__main__":
    unittest.main()
