"""Render representative machines with temporary chezmoi configuration."""
from pathlib import Path
import json
import subprocess
import tempfile
import tomllib
import unittest
from hyprland_tools import capture, native_verify

ROOT = Path(__file__).resolve().parents[1]


class TemplateTests(unittest.TestCase):
    def test_machine_matrix(self):
        cases = [("GAM-DEV001", "hyprland", None), ("personal-pc", "hyprland", None),
                 ("custom", "hyprland", [{"output": "DP-1", "mode": "preferred", "position": "auto", "scale": 1}]), ("server", "none", None)]
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            for hostname, desktop, override in cases:
                with self.subTest(hostname=hostname):
                    config = temp / "chezmoi.toml"
                    data = {"email": "test@example.invalid", "desktop": desktop, "hostname": hostname,
                            "form_factor": "laptop", "profile": "personal", "dev": True, "osid": "arch"}
                    content = "[data]\n" + "\n".join(f"{key} = {json.dumps(value)}" for key, value in data.items()) + "\n"
                    if override is not None:
                        content += "[[data.hyprland.monitors]]\n" + "\n".join(f"{key} = {json.dumps(value)}" for key, value in override[0].items()) + "\n"
                    config.write_text(content)
                    command = ["chezmoi", "--config", str(config), "--source", str(ROOT), "execute-template", "--file"]
                    rendered = subprocess.check_output(command + [str(ROOT / "dot_config/hypr/hyprland.lua.tmpl")], text=True)
                    pwa = subprocess.check_output(command + [str(ROOT / "dot_config/hypr/pwa.lua.tmpl")], text=True)
                    captured = capture(temp, rendered, pwa)
                    monitors = captured["monitors"]
                    self.assertEqual(len(monitors), 6 if hostname == "GAM-DEV001" else 1)
                    if override is not None:
                        self.assertEqual(monitors, override)
                    self.assertNotIn("switch:on:Lid Switch", rendered)
                    regenerated = tomllib.loads(subprocess.check_output(command + ["--init", str(ROOT / ".chezmoi.toml.tmpl")], text=True))
                    if override is not None:
                        self.assertEqual(regenerated["data"]["hyprland"]["monitors"], override)
                    ignore = subprocess.check_output(command + [str(ROOT / ".chezmoiignore")], text=True)
                    self.assertEqual(".local/bin/hypr-rescue" in ignore, desktop != "hyprland")
                    self.assertIn("suspend-recovery.md", ignore)
                    self.assertIn("tests/", ignore)
                    native_verify(temp)


if __name__ == "__main__":
    unittest.main()
