# XDG paths

The XDG directories separate configuration, installed data, cache, and persistent state.
Both zsh entry files set defaults when a parent process omits those variables.
An inherited `ZDOTDIR` still selects the shell configuration directory.
Explicit environment values remain unchanged.

Bun completions use `_bun` from `BUN_INSTALL` when that file exists.
Zsh also searches its normal completion directories.
Shell startup does not create `~/.bun` or run the Bun installer.

This configuration changes where tools write future files.
It does not move or delete existing data.
Before you remove an old directory, identify its owner and move any required data.

Run `python3 tests/xdg-zsh.py` to exercise shell startup in a temporary home directory.
