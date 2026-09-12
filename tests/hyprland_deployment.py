#!/usr/bin/env python3
"""Apply only to temporary destinations, including removal of legacy files."""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='hypr-deploy-') as directory:
    temp = Path(directory)
    config = temp / 'chezmoi.toml'
    for desktop in ['hyprland', 'none']:
        destination = temp / desktop
        folder = destination / '.config/hypr'
        folder.mkdir(parents=True)
        for name in ['hyprland.conf', 'pwa.conf', 'hyprlock.conf']:
            (folder / name).write_text('existing file\n')
        config.write_text(f'[data]\ndesktop="{desktop}"\nprofile="personal"\nhostname="test"\ndev=false\nform_factor="desktop"\nosid="arch"\nemail="test@example.invalid"\n')
        base = ['chezmoi', '--config', str(config), '--source', str(ROOT), '--destination', str(destination),
                '--persistent-state', str(temp / 'state.db'), '--cache', str(temp / 'cache')]
        if desktop == 'hyprland':
            result = subprocess.run(base + ['apply', '--exclude', 'scripts'] + [str(folder / name) for name in ['hyprland.lua', 'pwa.lua', 'hypridle.conf', 'hyprland.conf', 'pwa.conf']], text=True, capture_output=True)
            assert result.returncode == 0, result.stderr
            assert not (folder / 'hyprland.conf').exists() and not (folder / 'pwa.conf').exists()
            assert (folder / 'hyprland.lua').exists() and (folder / 'pwa.lua').exists()
        else:
            removed = subprocess.check_output(base + ['execute-template', '--file', str(ROOT / '.chezmoiremove')], text=True)
            assert not removed.strip()
            managed = subprocess.check_output(base + ['managed'], text=True)
            assert '.config/hypr/hyprland.lua' not in managed
        assert (folder / 'hyprlock.conf').read_text() == 'existing file\n'
print('PASS: temporary deployment retires only legacy Hyprland/PWA configs, with desktop gating')
