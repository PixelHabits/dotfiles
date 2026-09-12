#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.14"
# dependencies = []
# ///
"""Parse every machine's rendered config with the installed Hyprland, and check that region screenshots capture the frozen screen."""
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / 'dot_config/hypr/hyprland.lua.tmpl'

# Loads the config against a stand-in `hl` table and prints the command bound to one key.
LOAD = '''
local binds = {}
local function proxy(name)
    return setmetatable({}, {
        __index = function(_, key) return proxy(name .. "." .. key) end,
        __call = function(_, ...)
            if name == "hl.dsp.exec_cmd" then return (...) end
            if name == "hl.bind" then local keys, action = ...; binds[keys] = action end
            return proxy(name .. "()")
        end,
    })
end
hl = proxy("hl")
dofile(arg[1])
io.write(binds[arg[2]])
'''

FAKE = '''import os, signal, sys, time
tool = os.path.basename(sys.argv[0])
def record(name):
    with open(os.environ['CALLS'], 'a') as log: log.write(name + '\\n')
record(tool)
if tool == 'slurp' and 'CANCEL' not in os.environ: print('10,20 300x200')
if tool == 'grim': open(sys.argv[-1], 'w').close()
if tool == 'wl-copy': sys.stdin.read()
if tool == 'xdg-user-dir': print(os.environ['HOME'] + '/Pictures')
if tool == 'hyprpicker':
    signal.signal(signal.SIGTERM, lambda *_: (record('unfreeze'), sys.exit(0)))
    time.sleep(30)
'''

assert shutil.which('Hyprland'), 'Hyprland is not installed'
hosts = [*re.findall(r'eq \.hostname "([^"]+)"', TEMPLATE.read_text()), 'generic-host']

with tempfile.TemporaryDirectory(prefix='hypr-test-') as directory:
    temp = Path(directory)
    for host in hosts:
        config = temp / f'{host}.toml'
        config.write_text(f'[data]\nhostname = "{host}"\ndesktop = "hyprland"\n')
        rendered = temp / host / 'hyprland.lua'
        rendered.parent.mkdir()
        rendered.write_text(subprocess.check_output(
            ['chezmoi', '--config', str(config), '--source', str(ROOT), 'execute-template', '--file', str(TEMPLATE)], text=True))
        env = os.environ | {name: str(rendered.parent) for name in ['XDG_RUNTIME_DIR', 'XDG_STATE_HOME', 'XDG_CACHE_HOME']}
        result = subprocess.run(['Hyprland', '--verify-config', '--config', str(rendered)], env=env, capture_output=True, text=True)
        assert result.returncode == 0 and 'config ok' in result.stdout, f'{host}: {result.stdout}{result.stderr}'
    print(f'PASS: Hyprland parses the config for {", ".join(hosts)}')

    loader = temp / 'load.lua'
    loader.write_text(LOAD)
    region = subprocess.check_output(['lua', str(loader), str(temp / hosts[0] / 'hyprland.lua'), 'SUPER + SHIFT + S'], text=True)
    tools = temp / 'tools'
    tools.mkdir()
    fake = tools / 'fake'
    fake.write_text(f'#!{sys.executable}\n' + FAKE)
    fake.chmod(0o755)
    for tool in ['grim', 'slurp', 'wl-copy', 'notify-send', 'hyprpicker', 'xdg-user-dir']:
        (tools / tool).symlink_to(fake)

    def shoot(**extra):
        home = temp / 'home'
        shutil.rmtree(home, ignore_errors=True)
        home.mkdir()
        calls = temp / 'calls'
        calls.write_text('')
        env = {'PATH': f'{tools}:/usr/bin:/bin', 'HOME': str(home), 'CALLS': str(calls), **extra}
        subprocess.run(['sh', '-c', region], env=env, stdin=subprocess.DEVNULL, capture_output=True, timeout=20, check=True)
        return calls.read_text().split(), home

    order, home = shoot()
    assert order.index('grim') < order.index('unfreeze') and len(list((home / 'Pictures').glob('*.png'))) == 1, order
    order, home = shoot(CANCEL='1')
    assert 'grim' not in order and 'unfreeze' in order and not (home / 'Pictures').exists(), order
    print('PASS: region screenshots capture before the screen unfreezes, and a cancelled selection saves nothing')
