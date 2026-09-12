#!/usr/bin/env python3
"""Offline tests with temporary homes. Requires Python 3.11+, chezmoi, and Codex."""
import json
import os
from pathlib import Path
import shutil
import signal
import sys
import time
import subprocess
import tempfile
import tomllib
import unittest

SOURCE = Path(__file__).resolve().parents[2]


class CodexConfigTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="codex-config-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / "home with spaces"
        self.home.mkdir()
        self.target = self.home / ".config/codex/config.toml"
        self.target.parent.mkdir(parents=True)
        self.config = self.root / "chezmoi.toml"
        self.config.write_text('[data]\ndev = true\ndesktop = "none"\nprofile = "personal"\nhostname = "fixture"\n')
        self.env = {"HOME": str(self.home), "PATH": os.environ["PATH"],
                    "XDG_CONFIG_HOME": str(self.home / ".config"),
                    "XDG_CACHE_HOME": str(self.home / ".cache"),
                    "XDG_DATA_HOME": str(self.home / ".local/share"),
                    "XDG_STATE_HOME": str(self.home / ".local/state"),
                    "CODEX_HOME": str(self.target.parent),
                    "CODEX_SQLITE_HOME": str(self.home / ".local/state/codex")}
        self.command = [shutil.which("chezmoi"), "--source", str(SOURCE),
                        "--destination", str(self.home), "--config", str(self.config),
                        "--persistent-state", str(self.root / "state.boltdb")]

    def chezmoi(self, *args, check=True):
        return subprocess.run(self.command + list(args), env=self.env,
                              cwd=self.home, text=True, capture_output=True, check=check)

    def render(self):
        return self.chezmoi("cat", str(self.target)).stdout

    def test_fresh_home_and_idempotent_apply(self):
        rendered = self.render()
        value = tomllib.loads(rendered)
        self.assertNotIn("projects", value)
        self.assertNotIn("profile", value)
        self.assertNotIn("last_revision", value["marketplaces"]["caveman-repo"])
        self.assertEqual(value["sqlite_home"], self.env["CODEX_SQLITE_HOME"])
        self.chezmoi("apply", "--exclude", "scripts", str(self.target))
        self.assertEqual(self.target.read_text(), rendered)
        self.assertEqual(self.target.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.render(), rendered)
        self.assertEqual(self.chezmoi("diff", str(self.target)).stdout, "")

    def test_local_trust_plugins_and_overrides_survive(self):
        self.target.write_text('''model = "old-model"
[projects."/tmp/project with spaces"]
trust_level = "trusted"
[projects."/tmp/untrusted"]
trust_level = "untrusted"
[plugins."example@local"]
enabled = false
[mcp_servers.local-tool]
command = "example"
[mcp_servers.local-tool.env]
NPM_CONFIG_CACHE = "/custom/cache"
EXAMPLE_SETTING = "keep"
''')
        value = tomllib.loads(self.render())
        self.assertEqual(value["model"], "gpt-5.5")
        self.assertEqual(value["projects"]["/tmp/project with spaces"]["trust_level"], "trusted")
        self.assertEqual(value["projects"]["/tmp/untrusted"]["trust_level"], "untrusted")
        self.assertFalse(value["plugins"]["example@local"]["enabled"])
        env = value["mcp_servers"]["local-tool"]["env"]
        self.assertEqual(env["NPM_CONFIG_CACHE"], "/custom/cache")
        self.assertEqual(env["EXAMPLE_SETTING"], "keep")
        self.assertEqual(env["GOPATH"], str(self.home / ".local/share/go"))
        self.target.write_text(self.render())
        self.assertEqual(tomllib.loads(self.render()), value)

    def test_invalid_local_toml_fails_without_overwrite(self):
        self.target.write_text("[broken")
        result = self.chezmoi("apply", "--exclude", "scripts", str(self.target), check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.target.read_text(), "[broken")

    def test_dev_gating_and_work_personal_parity(self):
        personal = self.render()
        self.config.write_text(self.config.read_text().replace('"personal"', '"work"'))
        self.assertEqual(personal, self.render())
        self.config.write_text(self.config.read_text().replace('dev = true', 'dev = false'))
        managed = self.chezmoi("managed").stdout.splitlines()
        self.assertNotIn(".config/codex/config.toml", managed)
        self.assertNotIn("codex.md", managed)
        self.assertFalse(any(path.startswith("tests/codex") for path in managed))

    def test_shared_server_identity_changes_drop_old_connections(self):
        for existing in [
            '[mcp_servers.Bun]\ncommand = "example"\nargs = ["x"]\nenabled = false\n'
            '[mcp_servers.Bun.env]\nPRIVATE_SETTING = "fixture"\n',
            '[mcp_servers.chrome-devtools]\nurl = "https://example.invalid"\nenabled = false\n'
            '[mcp_servers.chrome-devtools.http_headers]\nAuthorization = "fixture"\n',
            '[mcp_servers.Bun]\nurl = "https://example.invalid"\nenabled = false\n'
            '[mcp_servers.Bun.http_headers]\nAuthorization = "fixture"\n',
        ]:
            with self.subTest(existing=existing):
                self.target.write_text(existing)
                rendered = self.render()
                self.assertNotIn("PRIVATE_SETTING", rendered)
                self.assertNotIn("Authorization", rendered)
                self.assertNotIn("https://example.invalid", rendered)
                self.target.write_text(rendered)
                value = tomllib.loads(rendered)
                name = "chrome-devtools" if "chrome-devtools" in existing else "Bun"
                self.assertFalse(value["mcp_servers"][name]["enabled"])
                if shutil.which("codex"):
                    subprocess.run([shutil.which("codex"), "mcp", "list", "--json"],
                                   env=self.env, cwd=self.home, capture_output=True,
                                   text=True, check=True, timeout=20)

    def test_optional_local_profile_alias(self):
        script = SOURCE / "dot_config/zsh/zshenv.d/20-codex.zsh"
        command = [shutil.which("zsh"), "-f", "-c",
                   'require_cmd() { command -v "$1" >/dev/null 2>&1; }; '
                   'source "$1"; alias codex', "fixture", str(script)]
        missing = subprocess.run(command, env=self.env, cwd=self.home, text=True, capture_output=True)
        self.assertEqual(missing.stdout, "")
        (self.target.parent / "local.config.toml").write_text('model = "local-model"\n')
        present = subprocess.run(command, env=self.env, cwd=self.home, text=True, capture_output=True)
        self.assertIn("--profile local", present.stdout)

    def test_installed_codex_accepts_rendered_mcp(self):
        if not shutil.which("codex"):
            self.skipTest("Codex is not installed")
        self.target.write_text(self.render())
        result = subprocess.run([shutil.which("codex"), "mcp", "list", "--json"],
                                cwd=self.home, env=self.env, capture_output=True,
                                text=True, check=True, timeout=20)
        servers = {item["name"]: item for item in json.loads(result.stdout)}
        self.assertIn("chrome-devtools", servers)
        self.assertFalse((self.home / ".codex").exists())
        self.assertFalse((self.home / ".bun").exists())
        self.assertFalse((self.home / ".npm").exists())
        self.assertFalse((self.home / "go").exists())

    def test_real_mcp_start_receives_xdg_without_shell_startup(self):
        if not shutil.which("codex"):
            self.skipTest("Codex is not installed")
        value = tomllib.loads(self.render())
        # A local fixture replaces every real server and plugin. No API credentials.
        server = value["mcp_servers"]["chrome-devtools"]
        marker = self.root / "mcp-env.json"
        fixture = self.root / "mcp.py"
        fixture.write_text("import json, os, pathlib\n"
                           + f"pathlib.Path({str(marker)!r}).write_text(json.dumps(dict(os.environ)))\n")
        server["command"] = sys.executable
        server["args"] = [str(fixture)]
        config = {
            "model": "offline-fixture", "model_provider": "offline",
            "model_providers": {"offline": {
                "name": "Offline fixture", "base_url": "http://127.0.0.1:9",
                "wire_api": "responses", "request_max_retries": 0}},
            "mcp_servers": {"fixture": server},
            "features": {"plugins": False},
            "log_dir": value["log_dir"], "sqlite_home": value["sqlite_home"],
        }
        # Use chezmoi's TOML encoder, with fixture data only.
        encoded = subprocess.run(self.command + ["execute-template", "--with-stdin",
                                 "{{ .chezmoi.stdin | fromJson | toToml }}"],
                                 input=json.dumps(config), env=self.env, cwd=self.home,
                                 capture_output=True, text=True, check=True).stdout
        self.target.write_text(encoded)
        proc = subprocess.Popen([shutil.which("codex"), "exec", "--skip-git-repo-check",
                                 "--sandbox", "read-only", "offline fixture"],
                                cwd=self.home, env=self.env, start_new_session=True,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            deadline = time.monotonic() + 15
            while not marker.exists() and proc.poll() is None and time.monotonic() < deadline:
                time.sleep(0.05)
            self.assertTrue(marker.exists(), "Codex did not start the local MCP fixture")
        finally:
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGTERM)
            proc.wait(timeout=5)
        received = json.loads(marker.read_text())
        for key, expected in server["env"].items():
            self.assertEqual(received.get(key), expected, key)
        for directory in (".codex", ".bun", ".npm", ".go", "go"):
            self.assertFalse((self.home / directory).exists(), directory)


if __name__ == "__main__":
    unittest.main()
