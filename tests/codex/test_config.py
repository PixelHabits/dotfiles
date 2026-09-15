#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.14"
# dependencies = []
# ///
"""Offline tests with temporary homes. Requires uv, chezmoi, and zsh."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import tomllib
import unittest

SOURCE = Path(__file__).resolve().parents[2]
SHARED = ".chezmoitemplates/codex/shared.toml.tmpl"
DATA = ('[data]\ndev = true\ndesktop = "none"\nprofile = "personal"\nhostname = "fixture"\n'
        'email = "fixture@example.invalid"\nform_factor = "server"\nosid = "arch"\n')


class CodexConfigTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="codex-config-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.home = self.root / "home with spaces"
        self.target = self.home / ".config/codex/config.toml"
        self.target.parent.mkdir(parents=True)
        self.config = self.root / "chezmoi.toml"
        self.config.write_text(DATA)
        self.env = {"HOME": str(self.home), "PATH": os.environ["PATH"]}
        self.command = [shutil.which("chezmoi"), "--source", str(SOURCE),
                        "--destination", str(self.home), "--config", str(self.config),
                        "--persistent-state", str(self.root / "state.boltdb")]

    def chezmoi(self, *args, check=True):
        return subprocess.run(self.command + list(args), env=self.env, cwd=self.home,
                              text=True, capture_output=True, check=check)

    def render(self):
        return tomllib.loads(self.chezmoi("cat", str(self.target)).stdout)

    def shared(self):
        return tomllib.loads(self.chezmoi("execute-template", "--file",
                                          str(SOURCE / SHARED)).stdout)

    def test_shared_keys_win_and_local_keys_survive(self):
        self.target.write_text('model = "old-model"\n'
                               '[projects."/tmp/project"]\ntrust_level = "trusted"\n'
                               '[notice]\nfast_default_opt_out = true\n'
                               '[plugins."example@local"]\nenabled = false\n')
        value = self.render()
        self.assertEqual(value["model"], self.shared()["model"])
        self.assertEqual(value["projects"]["/tmp/project"]["trust_level"], "trusted")
        self.assertTrue(value["notice"]["fast_default_opt_out"])
        self.assertTrue(value["notice"]["hide_full_access_warning"])
        self.assertFalse(value["plugins"]["example@local"]["enabled"])

    def test_shared_servers_replace_whole_table_and_local_servers_survive(self):
        self.target.write_text('[mcp_servers.chrome-devtools]\ncommand = "old"\n'
                               'enabled = false\n'
                               '[mcp_servers.chrome-devtools.env]\nSTALE = "drop"\n'
                               '[mcp_servers.local-tool]\ncommand = "example"\n'
                               '[mcp_servers.local-tool.env]\nKEEP = "yes"\n')
        servers = self.render()["mcp_servers"]
        self.assertEqual(servers["chrome-devtools"], self.shared()["mcp_servers"]["chrome-devtools"])
        self.assertEqual(servers["local-tool"]["env"]["KEEP"], "yes")

    def test_stdio_servers_forward_xdg_names_not_paths(self):
        for name, server in self.shared()["mcp_servers"].items():
            with self.subTest(server=name):
                if "command" not in server:
                    continue
                self.assertNotIn("env", server)
                self.assertIn("XDG_CACHE_HOME", server["env_vars"])
                self.assertIn("BUN_INSTALL", server["env_vars"])

    def test_missing_destination_is_created_private(self):
        self.chezmoi("apply", "--exclude", "scripts", str(self.target))
        self.assertEqual(tomllib.loads(self.target.read_text())["model"], self.shared()["model"])
        self.assertEqual(self.target.stat().st_mode & 0o777, 0o600)

    def test_invalid_destination_toml_aborts(self):
        self.target.write_text("[broken")
        result = self.chezmoi("apply", "--exclude", "scripts", str(self.target), check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.target.read_text(), "[broken")

    def test_home_redirects_render_and_dev_gate(self):
        script = self.root / "redirect.zsh"
        script.write_text(self.chezmoi("execute-template", "--file", str(
            SOURCE / "dot_config/zsh/zshenv.d/20-codex.zsh.tmpl")).stdout + "env -0\n")
        output = subprocess.check_output([shutil.which("zsh"), "-f", str(script)],
                                         env=self.env | {"CODEX_SQLITE_HOME": "/custom"}, cwd=self.home)
        actual = dict(item.decode().split("=", 1) for item in output.split(b"\0") if item)
        self.assertEqual(actual["CODEX_HOME"], str(self.home / ".config/codex"))
        self.assertEqual(actual["CODEX_SQLITE_HOME"], "/custom")
        self.config.write_text(DATA.replace("dev = true", "dev = false"))
        managed = self.chezmoi("managed").stdout.splitlines()
        for path in (".config/codex/config.toml", ".config/zsh/zshenv.d/20-codex.zsh",
                     ".config/environment.d/22-codex.conf"):
            self.assertNotIn(path, managed)


if __name__ == "__main__":
    unittest.main()
