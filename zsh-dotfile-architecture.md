# ZSH Dotfiles Architecture

## Overview

A modular, XDG-compliant zsh configuration using Unix drop-in directory conventions with numbered scripts and deterministic load order.

**Tool boundary:** Zsh scripts define runtime shell behavior only. They never install packages or create directories outside of `$XDG_STATE_HOME/zsh` and `$XDG_CACHE_HOME/zsh`. Package installation is Ansible's job. Per-host file presence is chezmoi's job.

## Bootstrap Chain

```
~/.zshenv                         (always, all shells)
 └─ exports XDG, sets ZDOTDIR
 └─ sources $ZDOTDIR/.zshenv

$ZDOTDIR/.zshenv                  (always, all shells)
 └─ defines source_dir() helper
 └─ sources zshenv.d/*.zsh

$ZDOTDIR/.zprofile                (login shells only)
 └─ sources zprofile.d/*.zsh

$ZDOTDIR/.zshrc                   (interactive shells only)
 └─ sources zshrc.d/*.zsh
```

## Directory Structure

```
~/.zshenv                              <- bootstrap only (XDG + ZDOTDIR)

~/.config/zsh/
├── .zshenv                            <- defines source_dir, loads zshenv.d/
├── .zprofile                          <- loads zprofile.d/
├── .zshrc                             <- loads zshrc.d/
├── zshenv.d/                          <- ALL shells (env vars, PATH)
├── zprofile.d/                        <- LOGIN shells (session startup)
└── zshrc.d/                           <- INTERACTIVE shells (aliases, prompt)

~/.config/p10k/p10k.zsh               <- powerlevel10k config
~/.local/share/oh-my-zsh/             <- OMZ installation (Ansible manages)
~/.local/state/zsh/history            <- shell history
~/.cache/zsh/zcompdump-*              <- completion cache
```

## Numbering Convention

| Band    | Purpose                     | Examples                          |
|---------|-----------------------------|-----------------------------------|
| `00-09` | Core infrastructure         | logging, privacy, xdg redirects   |
| `10-19` | Core shell policy           | path, history, keybindings        |
| `20-39` | Frameworks & integrations   | oh-my-zsh, fzf, zoxide            |
| `40-69` | Interactive UX              | aliases, functions, completions   |
| `70+`   | Late / optional             | summary, diagnostics              |

## Phase Purity

| Phase       | Allowed                                    | Forbidden                    |
|-------------|--------------------------------------------|------------------------------|
| `zshenv.d/` | env vars, PATH, logging helpers            | output, prompts, subprocesses|
| `zprofile.d/`| session startup, tty gates, agent startup | interactive-only features    |
| `zshrc.d/`  | options, aliases, functions, prompt        | nothing                      |

## Key Patterns

**The `source_dir()` helper** (defined in `$ZDOTDIR/.zshenv`):
```zsh
source_dir() {
	for f in "$1"/*.zsh(N-.r); do
		source "$f"
	done
}
```
Glob qualifiers: `N` = nullglob, `-` = follow symlinks, `.` = regular file, `r` = readable. Files sort lexicographically, so numeric prefixes enforce order.

**Logging infrastructure** (defined in `00-logging.zsh`):
- `zlog "msg"` — prints only when `ZSH_BOOT_DEBUG=1`, silent during p10k instant prompt
- `zwarn "msg"` — accumulates warnings, prints to stderr in interactive shells only
- `require_cmd name` — checks command existence via `$+commands[name]`, calls `zwarn` on miss

**Fail-open pattern:**
```zsh
require_cmd fzf || return 0
```
Missing tools skip cleanly, never crash the shell.

**Side-effect correction in the same file:**
```zsh
source $ZSH/oh-my-zsh.sh
# OMZ sets share_history, undo it here
unsetopt share_history
```
Never use a late file to repair an early file.

**File deprecation:**
```
22-atuin.zsh.disabled     <- ignored by *.zsh glob
```

## XDG Conventions

The bootstrap `~/.zshenv` exports all XDG variables. Every other file uses bare `$XDG_*` with no fallbacks.

| Variable          | Purpose              | Example contents                    |
|-------------------|----------------------|-------------------------------------|
| `XDG_CONFIG_HOME` | User configuration   | zsh/, git/config, p10k/             |
| `XDG_DATA_HOME`   | Installed artifacts  | oh-my-zsh/, cargo/, rustup/         |
| `XDG_CACHE_HOME`  | Regenerable cache    | zsh/zcompdump-*, npm/               |
| `XDG_STATE_HOME`  | Persistent state     | zsh/history, less/history           |

## Per-Host File Presence

Chezmoi controls which files exist via `.chezmoiignore`. If a file is deployed, it runs unconditionally. No inline OS detection in shell scripts.

See `workstation-bootstrap.md` for the gating matrix.

## Common Tasks

| Task                      | How                                                    |
|---------------------------|--------------------------------------------------------|
| Add tool integration      | Create `zshrc.d/2x-tool.zsh`, guard with `require_cmd` |
| Add XDG redirect          | Add to `06-xdg-apps.zsh` AND `site.yml` xdg_environment|
| Disable script            | Rename: `mv foo.zsh foo.zsh.disabled`                  |
| Debug slow startup        | `ZSH_BOOT_DEBUG=1 zsh`                                 |
