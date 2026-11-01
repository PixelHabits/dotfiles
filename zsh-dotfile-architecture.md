# ZSH Dotfiles Architecture

## Overview

A modular, XDG-compliant zsh configuration using Unix drop-in directory conventions with numbered scripts and deterministic load order.

**Tool boundary:** Zsh scripts define runtime shell behavior only. They never install packages or create directories outside of `$XDG_STATE_HOME/zsh` and `$XDG_CACHE_HOME/zsh`. Package installation is Ansible's job. Per-host file presence is chezmoi's job.

## Bootstrap Chain

```
~/.zshenv                         (when ZDOTDIR is unset)
 └─ defaults XDG_CONFIG_HOME, sets ZDOTDIR
 └─ sources $ZDOTDIR/.zshenv

$ZDOTDIR/.zshenv                  (also a direct entry when ZDOTDIR is inherited)
 └─ defaults all four XDG base directories from the shared map
 └─ defines source_dir() helper
 └─ sources zshenv.d/*.zsh

$ZDOTDIR/.zprofile                (login shells only)
 └─ sources zprofile.d/*.zsh

$ZDOTDIR/.zshrc                   (interactive shells only)
 └─ sources zshrc.d/*.zsh
```

## Directory Structure

```
~/.zshenv                              <- bootstrap only (XDG_CONFIG_HOME + ZDOTDIR)

~/.config/zsh/
├── .zshenv                            <- sets base defaults, loads zshenv.d/
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

The shared map in `.chezmoitemplates/xdg-env.toml.tmpl` has two tables.
`base` holds the four XDG directories and `ZDOTDIR`. `apps` holds tool paths.
The full `.zshenv` renders `base` before it loads any drop-ins.
`zshenv.d/06-xdg-apps.zsh` renders `apps`. `environment.d/10-xdg.conf` renders both.
Shell defaults fill unset or empty values and preserve existing nonempty values.

The home bootstrap only locates the full configuration.
When `ZDOTDIR` is already set, zsh reads that directory's `.zshenv` directly.
Both paths therefore receive the same defaults.
Application defaults use the rendered home directory. A custom base variable does not relocate every application automatically.

| Launch path | Environment source |
| --- | --- |
| Terminal or ordinary zsh script on Linux or macOS | The full `.zshenv` and its drop-ins |
| SSH shell or command when the remote account uses zsh | The same zsh startup files |
| Linux systemd user service | `environment.d/10-xdg.conf` |
| Linux desktop application | The parent process or the desktop's import of the systemd user environment |

Zsh startup files do not configure applications that macOS starts outside a shell.
The LaunchAgent described below supplies their environment through launchd.
Existing processes retain their previous environment.
Programs that ignore XDG variables still need their own directory configuration.

Run `uv run tests/xdg/test_defaults.py` to test both startup paths and the shared renderers in temporary homes.
These tests do not establish live SSH behavior or native macOS session behavior.

| Variable          | Purpose              | Example contents                    |
|-------------------|----------------------|-------------------------------------|
| `XDG_CONFIG_HOME` | User configuration   | zsh/, git/config, p10k/             |
| `XDG_DATA_HOME`   | Installed artifacts  | oh-my-zsh/, cargo/, rustup/         |
| `XDG_CACHE_HOME`  | Regenerable cache    | zsh/zcompdump-*, npm/               |
| `XDG_STATE_HOME`  | Persistent state     | zsh/history, less/history           |

### macOS applications

The LaunchAgent at `Library/LaunchAgents/com.pixelhabits.xdg-env.plist` renders the same map as the shell and Linux service files.
It runs `launchctl setenv` for each variable at login.
Applications that launchd starts afterwards inherit these values.
The `xdg-launchagent.sh` script reloads the agent after `chezmoi apply` changes the map.
If there is no GUI session, the reload waits for the next login.

Applications that are already running retain their previous environment.
Restart them after the LaunchAgent loads.
macOS lists the agent under Login Items as a background item.

Run `uv run tests/xdg/test_env_renderers.py` to test rendering and reload behavior with a temporary launchctl substitute.
These tests do not establish native macOS login or GUI inheritance.

## Per-Host File Presence

Chezmoi controls which files exist via `.chezmoiignore`. If a file is deployed, it runs unconditionally. No inline OS detection in shell scripts.

See `workstation-bootstrap.md` for the gating matrix.

## Common Tasks

| Task                      | How                                                    |
|---------------------------|--------------------------------------------------------|
| Add tool integration      | Create `zshrc.d/2x-tool.zsh`, guard with `require_cmd` |
| Add XDG redirect          | Add the path to `.chezmoitemplates/xdg-env.toml.tmpl`; update `site.yml` only if Ansible needs it |
| Disable script            | Rename: `mv foo.zsh foo.zsh.disabled`                  |
| Debug slow startup        | `ZSH_BOOT_DEBUG=1 zsh`                                 |

Run `uv run tests/xdg/test_env_renderers.py` to test all three renderers and the reload script with temporary homes.
The script requires Python 3.14 or later, chezmoi, and zsh. It has no Python package dependencies.
The tests use a local `launchctl` substitute. Actual macOS login and GUI inheritance require a Mac.
