#!/usr/bin/env python3
"""Exercise both zsh entry paths in isolated homes."""
from pathlib import Path
import os, shutil, subprocess, tempfile
ROOT = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix="xdg-zsh-") as directory:
    home = Path(directory)
    default = home / ".config/zsh"
    inherited = home / "custom-zsh"
    for zdot in (default, inherited):
        zdot.mkdir(parents=True)
        (zdot / "zshenv.d").mkdir()
        shutil.copy2(ROOT / "dot_config/zsh/dot_zshenv", zdot / ".zshenv")
        (zdot / "zshenv.d/99-count.zsh").write_text('export LOADS=$(( ${LOADS:-0} + 1 ))\n')
    shutil.copy2(ROOT / "dot_zshenv", home / ".zshenv")
    variables = ["XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME", "ZDOTDIR"]
    expected = [str(home / suffix) for suffix in (".config", ".cache", ".local/share", ".local/state", ".config/zsh")]
    for overrides in ({}, {"ZDOTDIR": str(inherited)}, {"XDG_CACHE_HOME": str(home / "cache override"), "ZDOTDIR": str(inherited)}):
        env = {"HOME": str(home), "PATH": os.environ["PATH"], **overrides}
        result = subprocess.run(["zsh", "-c", 'print -rl -- "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME" "$XDG_DATA_HOME" "$XDG_STATE_HOME" "$ZDOTDIR" "$LOADS"'], env=env, text=True, capture_output=True, check=True)
        assert result.stderr == "", result.stderr
        assert result.stdout.splitlines() == [overrides.get(k, v) for k, v in zip(variables, expected)] + ["1"]
    bun = home / "bun install"
    bun.mkdir()
    (bun / "_bun").write_text('#compdef bun\n_bun() { _arguments "--help[show help]"; }\ncompdef _bun bun\n')
    script = 'zlog() { :; }; source "$TEST_COMPLETIONS"; print -r -- "${_comps[bun]}"'
    env = {"HOME": str(home), "ZDOTDIR": str(inherited), "PATH": os.environ["PATH"], "BUN_INSTALL": str(bun), "TEST_COMPLETIONS": str(ROOT / "dot_config/zsh/zshrc.d/50-completions.zsh")}
    result = subprocess.run(["zsh", "-c", script], env=env, text=True, capture_output=True, check=True)
    assert result.stderr == "", result.stderr
    assert result.stdout.splitlines() == ["_bun"], result.stdout
    assert not (home / ".bun").exists()
    assert list((home / ".cache/zsh").glob("zcompdump-*"))
print("PASS: default/inherited zsh entry, override preservation, single load, and XDG Bun completions")
