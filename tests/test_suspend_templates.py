#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.14"
# dependencies = []
# ///
"""Render representative machines with temporary chezmoi configuration."""
from pathlib import Path
import json
import os
import shutil
import subprocess
import tempfile
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[1]


class TemplateTests(unittest.TestCase):
    def test_machine_matrix(self):
        cases = [("GAM-DEV001", "hyprland", None), ("personal-pc", "hyprland", None),
                 ("custom", "hyprland", ["DP-1, preferred, auto, 1"]), ("server", "none", None)]
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            for hostname, desktop, override in cases:
                with self.subTest(hostname=hostname):
                    config = temp / "chezmoi.toml"
                    data = {"email": "test@example.invalid", "desktop": desktop, "hostname": hostname,
                            "form_factor": "laptop" if hostname in ["GAM-DEV001", "custom"] else "desktop", "profile": "personal", "dev": True, "osid": "arch"}
                    content = "[data]\n" + "\n".join(f"{key} = {json.dumps(value)}" for key, value in data.items()) + "\n"
                    if override is not None:
                        content += '[data.hyprland]\nlaptop_output = "desc:Custom panel"\nmonitors = ' + json.dumps(override) + "\n"
                    config.write_text(content)
                    command = ["chezmoi", "--config", str(config), "--source", str(ROOT), "execute-template", "--file"]
                    rendered = subprocess.check_output(command + [str(ROOT / "dot_config/hypr/hyprland.conf.tmpl")], text=True)
                    monitors = [line for line in rendered.splitlines() if line.startswith("monitor =")]
                    self.assertEqual(len(monitors), 6 if hostname == "GAM-DEV001" else 1)
                    if override is not None:
                        self.assertEqual(monitors, ["monitor = " + override[0]])
                    self.assertEqual("switch:on:Lid Switch" in rendered, hostname in ["GAM-DEV001", "custom"])
                    self.assertEqual("switch:off:Lid Switch" in rendered, hostname in ["GAM-DEV001", "custom"])
                    idle = subprocess.check_output(command + [str(ROOT / "dot_config/hypr/hypridle.conf.tmpl")], text=True)
                    self.assertEqual("grep -q open /proc/acpi/button/lid/*/state" in idle, data["form_factor"] == "laptop")
                    self.assertIn("allow_session_lock_restore = true", rendered)
                    regenerated = tomllib.loads(subprocess.check_output(command + ["--init", str(ROOT / ".chezmoi.toml.tmpl")], text=True))
                    if override is not None:
                        self.assertEqual(regenerated["data"]["hyprland"]["monitors"], override)
                        self.assertEqual(regenerated["data"]["hyprland"]["laptop_output"], "desc:Custom panel")
                    ignore = subprocess.check_output(command + [str(ROOT / ".chezmoiignore")], text=True)
                    self.assertEqual(".local/bin/hypr-rescue" in ignore, desktop != "hyprland")
                    self.assertIn("suspend-recovery.md", ignore)
                    self.assertIn("tests/", ignore)
                    if shutil.which("Hyprland"):
                        conf = temp / "hyprland.conf"
                        conf.write_text(rendered)
                        env = os.environ | {"XDG_RUNTIME_DIR": directory, "XDG_STATE_HOME": directory, "XDG_CACHE_HOME": directory}
                        result = subprocess.run(["Hyprland", "--verify-config", "--config", str(conf)], env=env, capture_output=True, text=True)
                        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
