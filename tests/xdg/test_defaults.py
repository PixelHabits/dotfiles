#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.14"
# dependencies = []
# ///
"""Render Linux/macOS defaults and run isolated zsh startup on the test host."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import tomllib
import unittest

SOURCE = Path(__file__).resolve().parents[2]
PARTIAL = ".chezmoitemplates/xdg-env.toml.tmpl"
DATA = ('[data]\ndev = true\ndesktop = "none"\nprofile = "personal"\nhostname = "fixture"\n'
        'email = "fixture@example.invalid"\nform_factor = "server"\nosid = "arch"\n')


class XdgDefaultsTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="xdg-defaults-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.home = self.root / "home with spaces"
        self.home.mkdir()
        self.zdot = self.home / ".config/zsh"
        (self.zdot / "zshenv.d").mkdir(parents=True)
        self.config = self.root / "chezmoi.toml"
        self.env = {"HOME": str(self.home), "PATH": os.environ["PATH"], "TERM": "dumb"}
        self.command = [shutil.which("chezmoi"), "--source", str(SOURCE),
                        "--destination", str(self.home), "--config", str(self.config),
                        "--persistent-state", str(self.root / "state.boltdb")]
        self.use_os("linux")

    def use_os(self, name):
        self.config.write_text(DATA + f'[data.chezmoi]\nos = "{name}"\n')

    def chezmoi(self, *args):
        return subprocess.check_output(self.command + list(args), env=self.env,
                                       cwd=self.home, text=True)

    def render(self, path):
        return self.chezmoi("execute-template", "--file", str(SOURCE / path))

    def defaults(self):
        table = tomllib.loads(self.render(PARTIAL))
        return table["base"] | table["apps"]

    def install_shell(self):
        shutil.copyfile(SOURCE / "dot_zshenv", self.home / ".zshenv")
        (self.zdot / ".zshenv").write_text(self.render("dot_config/zsh/dot_zshenv.tmpl"))
        (self.zdot / "zshenv.d/06-xdg-apps.zsh").write_text(
            self.render("dot_config/zsh/zshenv.d/06-xdg-apps.zsh.tmpl"))
        (self.zdot / "zshenv.d/99-count.zsh").write_text(
            "typeset -gi _xdg_load_count; (( ++_xdg_load_count ))\n")

    def shell(self, overrides=None, flags="-c", command=None):
        command = command or "print -rn -- XDG_TEST_LOAD_COUNT=$_xdg_load_count$'\\0'; env -0"
        result = subprocess.run([shutil.which("zsh"), "-d", flags, command],
                                env=self.env | (overrides or {}), cwd=self.home,
                                capture_output=True, check=True)
        self.assertEqual(result.stderr, b"")
        return dict(item.decode().split("=", 1) for item in result.stdout.split(b"\0") if item)

    def test_systemd_renderer_matches_shared_map(self):
        rendered = self.render("dot_config/environment.d/10-xdg.conf.tmpl")
        values = dict(line.split("=", 1) for line in rendered.splitlines()
                      if line and not line.startswith("#"))
        self.assertEqual(values, self.defaults())

    def test_both_startup_paths_get_all_defaults_once(self):
        for platform in ("linux", "darwin"):
            self.use_os(platform)
            self.install_shell()
            expected = self.defaults()
            for flags in ("-c", "-lc", "-ic"):
                for inherited in ({}, {"ZDOTDIR": str(self.zdot)}):
                    with self.subTest(platform=platform, flags=flags, inherited=bool(inherited)):
                        actual = self.shell(inherited, flags)
                        self.assertEqual({key: actual.get(key) for key in expected}, expected)
                        self.assertEqual(actual["XDG_TEST_LOAD_COUNT"], "1")

    def test_empty_values_fall_back_and_nonempty_overrides_survive(self):
        self.install_shell()
        defaults = self.defaults()
        empty = {key: "" for key in defaults if key != "ZDOTDIR"}
        actual = self.shell(empty | {"ZDOTDIR": str(self.zdot)})
        self.assertEqual({key: actual.get(key) for key in defaults}, defaults)
        overrides = {key: str(self.root / f"custom {key}") for key in defaults if key != "ZDOTDIR"}
        actual = self.shell(overrides | {"ZDOTDIR": str(self.zdot)})
        self.assertEqual({key: actual.get(key) for key in overrides}, overrides)
        custom_config = self.root / "custom config"
        shutil.copytree(self.zdot, custom_config / "zsh")
        actual = self.shell({"XDG_CONFIG_HOME": str(custom_config)})
        self.assertEqual(actual["ZDOTDIR"], str(custom_config / "zsh"))
        self.assertEqual(actual["XDG_CONFIG_HOME"], str(custom_config))
        self.assertEqual(actual["XDG_TEST_LOAD_COUNT"], "1")

    def test_shell_children_inherit_tool_defaults(self):
        self.install_shell()
        actual = self.shell(command="/bin/sh -c 'env -0'")
        self.assertEqual({key: actual.get(key) for key in self.defaults()}, self.defaults())

    def test_test_files_stay_in_source(self):
        managed = self.chezmoi("managed").splitlines()
        self.assertFalse(any(path.startswith("tests/") for path in managed))


if __name__ == "__main__":
    unittest.main()
