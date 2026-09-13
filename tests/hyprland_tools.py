"""Capture Lua declarations and run the installed compositor's parser only."""
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def capture(directory, hyprland, pwa):
    directory = Path(directory)
    (directory / 'hyprland.lua').write_text(hyprland)
    (directory / 'pwa.lua').write_text(pwa)
    result = subprocess.check_output(['lua', str(ROOT / 'tests/hyprland_capture.lua'), str(directory)], text=True)
    return json.loads(result)


def native_verify(directory):
    if not shutil.which('Hyprland'):
        print('SKIP: Hyprland is not installed; native Lua parsing was not verified')
        return
    directory = Path(directory)
    env = os.environ | {name: str(directory) for name in ['XDG_RUNTIME_DIR', 'XDG_STATE_HOME', 'XDG_CACHE_HOME']}
    result = subprocess.run(['Hyprland', '--verify-config', '--config', str(directory / 'hyprland.lua')], env=env, capture_output=True, text=True)
    assert result.returncode == 0 and 'config ok' in result.stdout, result.stdout + result.stderr
