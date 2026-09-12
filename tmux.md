# Tmux projects

Run `tmux-sessionizer` to select a Git checkout.
The picker searches `~/Developer` and the chezmoi worktree directory.
It includes Git worktrees and excludes `.bare`, `.git`, dependency, and vendor directories.
The search stops after four directory levels.

To replace the search roots, create `~/.config/tmux/project-roots`.
Use one path per line, with absolute paths or a `~/` prefix.
Blank lines and lines that start with `#` are ignored.
The file stays local to the machine.

Run `tmux-sessionizer /path/to/project` to open any directory directly.
Session names include a path checksum so different `main` worktrees stay separate.
The launcher checks the stored project path before it reuses a session.

Extended keys use CSI-u when the installed tmux version supports that option.
The terminal also needs support for extended keys.

Run `python3 tests/tmux-sessionizer.py` for isolated routing tests.
