#!/usr/bin/env python3
import json, subprocess, tempfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix="waybar-tests-") as temp:
    config=Path(temp)/"chezmoi.toml"
    config.write_text('[data]\nemail="test@example.invalid"\nhostname="test"\nosid="arch"\ndesktop="hyprland"\nprofile="personal"\nform_factor="desktop"\ndev=true\n')
    for form in ("laptop","desktop"):
        text=subprocess.check_output(['chezmoi','--config',str(config),'--source',str(root),'--override-data',json.dumps({'form_factor':form}),'cat',str(Path.home()/'.config/waybar/config.jsonc')],text=True)
        data=json.loads(text)
        assert ('battery' in data['modules-right']) == (form=='laptop')
        assert ('backlight' in data['modules-right']) == (form=='laptop')
        assert 'custom/media' not in data and 'exec' not in data['mpris']
        assert data['mpris']['format'] == '{player_icon} {dynamic}'
        assert 'mpd' not in data and 'sway/language' not in data['modules-right']
        assert 'timezone' not in data['clock']
        assert data['hyprland/submap']['format']=='<span style="italic">{}</span>'
        assert data['hyprland/workspaces']['format-icons']['linear']=='◩'
        for section in ('modules-left','modules-center','modules-right'):
            assert all(name in data or name == 'hyprland/window' for name in data[section])
print('PASS: laptop/desktop modules, local timezone, valid JSON, shared icons, and module definitions')
