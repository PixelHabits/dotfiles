#!/usr/bin/env python3
"""Offline tests with temporary homes. Requires Python 3.11+, chezmoi, and zsh."""
import hashlib
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import tempfile
import tomllib
import unittest

SOURCE = Path(__file__).resolve().parents[2]
LABEL = "com.pixelhabits.xdg-env"
PLIST = f"Library/LaunchAgents/{LABEL}.plist"
SERVICE = ".config/environment.d/10-xdg.conf"
SCRIPT = "xdg-launchagent.sh"
PARTIAL = ".chezmoitemplates/xdg-env.toml.tmpl"
SHELL = "dot_config/zsh/zshenv.d/06-xdg-apps.zsh.tmpl"
RELOAD = "run_onchange_after_xdg-launchagent.sh.tmpl"
DATA = ('[data]\ndev = true\ndesktop = "none"\nprofile = "personal"\nhostname = "fixture"\n'
        'email = "fixture@example.invalid"\nform_factor = "server"\nosid = "arch"\n')


class EnvRenderersTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="xdg-env-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / "home with spaces"
        self.home.mkdir()
        self.config = self.root / "chezmoi.toml"
        self.env = {"HOME": str(self.home), "PATH": os.environ["PATH"]}
        self.command = [shutil.which("chezmoi"), "--source", str(SOURCE),
                        "--destination", str(self.home), "--config", str(self.config),
                        "--persistent-state", str(self.root / "state.boltdb")]
        self.use_os("darwin")

    def use_os(self, name):
        self.config.write_text(DATA + f'[data.chezmoi]\nos = "{name}"\n')

    def chezmoi(self, *args):
        return subprocess.run(self.command + list(args), env=self.env, cwd=self.home,
                              text=True, capture_output=True, check=True).stdout

    def managed(self):
        return set(self.chezmoi("managed", "--include", "dirs,files,scripts").splitlines())

    def render(self, path):
        return self.chezmoi("execute-template", "--file", str(Path(self.command[2]) / path))

    def defaults(self):
        return tomllib.loads(self.render(PARTIAL))

    def plist_assignments(self):
        plist = plistlib.loads(self.chezmoi("cat", str(self.home / PLIST)).encode())
        self.assertEqual(plist["Label"], LABEL)
        self.assertTrue(plist["RunAtLoad"])
        self.assertEqual(plist["ProgramArguments"][:2], ["/bin/sh", "-c"])
        self.assertEqual(len(plist["ProgramArguments"]), 3)
        # A launchctl shim records the exact arguments the shell hands over.
        shim = self.root / "bin"
        shim.mkdir(exist_ok=True)
        log = self.root / "launchctl.log"
        (shim / "launchctl").write_text('#!/bin/sh\nprintf "%s\\0" "$@" >> "$LAUNCHCTL_LOG"\n')
        (shim / "launchctl").chmod(0o755)
        env = self.env | {"PATH": f"{shim}:{self.env['PATH']}", "LAUNCHCTL_LOG": str(log)}
        subprocess.run(["/bin/sh", "-c", plist["ProgramArguments"][2]], env=env,
                       cwd=self.home, check=True, capture_output=True)
        calls = log.read_bytes().split(b"\0")[:-1]
        self.assertEqual(len(calls) % 3, 0)
        assignments = {}
        for verb, name, value in zip(calls[::3], calls[1::3], calls[2::3]):
            self.assertEqual(verb, b"setenv")
            assignments[name.decode()] = value.decode()
        self.assertEqual(len(assignments), len(calls) // 3)
        return assignments

    def test_plist_defines_exactly_the_shared_variables(self):
        self.assertEqual(self.plist_assignments(), self.defaults())

    def test_plist_values_match_the_zsh_fallback(self):
        assignments = self.plist_assignments()
        rendered = self.render(SHELL)
        exported = {line.split("=", 1)[0].removeprefix("export ")
                    for line in rendered.splitlines() if line.startswith("export ")}
        self.assertTrue(exported)
        self.assertLessEqual(exported, set(assignments))
        script = self.root / "redirects.zsh"
        script.write_text(rendered + "\nenv -0\n")
        output = subprocess.check_output([shutil.which("zsh"), "-f", str(script)],
                                         env=self.env, cwd=self.home)
        actual = dict(item.decode().split("=", 1) for item in output.split(b"\0") if item)
        for name in exported:
            self.assertEqual(actual[name], assignments[name], name)

    def test_ignore_follows_the_operating_system(self):
        managed = self.managed()
        self.assertIn(PLIST, managed)
        self.assertIn(SCRIPT, managed)
        self.assertNotIn(SERVICE, managed)
        self.use_os("linux")
        managed = self.managed()
        self.assertNotIn(PLIST, managed)
        self.assertNotIn(SCRIPT, managed)
        self.assertFalse(any(path.startswith("Library") for path in managed))
        if shutil.which("systemctl") and Path("/run/systemd/system").exists():
            self.assertIn(SERVICE, managed)
        self.assertFalse(any(path.startswith("tests/") for path in managed))

    def test_reload_script_tracks_the_plist_and_the_shared_variables(self):
        script = self.render(RELOAD)
        subprocess.run(["/bin/sh", "-n"], input=script, text=True, check=True)
        self.assertIn(hashlib.sha256((SOURCE / "Library/LaunchAgents" / f"{LABEL}.plist.tmpl")
                                     .read_bytes()).hexdigest(), script)
        partial_hash = hashlib.sha256(self.render(PARTIAL).encode()).hexdigest()
        self.assertIn(partial_hash, script)
        self.assertIn(f"plist='{self.home / PLIST}'", script)
        self.assertIn("gui/$(id -u)", script)
        self.assertIn('launchctl print "$domain"', script)
        self.assertIn("exit 0", script)
        snapshot = self.root / "source"
        shutil.copytree(SOURCE / ".chezmoitemplates", snapshot / ".chezmoitemplates")
        shutil.copytree(SOURCE / "Library", snapshot / "Library")
        for path in (".chezmoiignore", RELOAD):
            shutil.copy2(SOURCE / path, snapshot / path)
        defaults = snapshot / PARTIAL
        defaults.write_text(defaults.read_text().replace(".local/share/go", ".local/share/go-next"))
        self.command[2] = str(snapshot)
        changed = self.render(RELOAD)
        self.assertNotIn(partial_hash, changed)
        self.assertNotEqual(changed, script)


if __name__ == "__main__":
    unittest.main()
