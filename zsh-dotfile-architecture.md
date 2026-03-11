# ZSH Dotfiles Architecture

## Purpose

This document describes the zsh shell configuration: boot chain,
drop-in directory conventions, file-by-file reference, and every
rule governing how shell scripts are written and organized.

For workstation bootstrap, package management, chezmoi deployment,
and Ansible playbook architecture, see `workstation-bootstrap.md`.

---

## System Overview

A modular, XDG-compliant zsh configuration using Unix drop-in
directory conventions with numbered scripts, deterministic load
order, and strict phase separation.

### Tool boundary

Zsh scripts define **runtime shell behavior only**. They never
install packages, clone repos, or create directories outside of
`$XDG_STATE_HOME/zsh` and `$XDG_CACHE_HOME/zsh` (which are
safety-checked with `mkdir -p` at point of use).

Package installation and directory scaffolding are Ansible's job.
Per-host file presence is chezmoi's job. See `workstation-bootstrap.md`.

---

## Bootstrap Chain

Zsh processes startup files in this order. The entire architecture
depends on this sequence:

```text
1. ~/.zshenv                          (always, all shells)
   └─ exports XDG variables
   └─ sets ZDOTDIR=$XDG_CONFIG_HOME/zsh
   └─ sources $ZDOTDIR/.zshenv

2. $ZDOTDIR/.zshenv                   (always, all shells)
   └─ defines source_dir() helper
   └─ sources zshenv.d/*.zsh

3. $ZDOTDIR/.zprofile                 (login shells only)
   └─ sources zprofile.d/*.zsh

4. $ZDOTDIR/.zshrc                    (interactive shells only)
   └─ sources zshrc.d/*.zsh
```

### The bootstrap `~/.zshenv`

```zsh
export XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$HOME/.cache}"
export XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
export XDG_STATE_HOME="${XDG_STATE_HOME:-$HOME/.local/state}"

export ZDOTDIR="$XDG_CONFIG_HOME/zsh"

if [[ -r "$ZDOTDIR/.zshenv" ]]; then
  source "$ZDOTDIR/.zshenv"
fi
```

**Rules for this file:**

- Must stay tiny forever
- Runs for interactive, login, non-interactive, SSH, cron, scp
- No helper functions, no heavy logic, no output
- This is the **only** file that uses `${VAR:-fallback}` for XDG
  variables

### The loader helper

Defined once in `$ZDOTDIR/.zshenv`, reused by `.zprofile` and
`.zshrc`:

```zsh
source_dir() {
  for f in "$1"/*.zsh(N-.r); do
    source "$f"
  done
}
```

Glob qualifiers: `N` = nullglob, `-` = follow symlinks to regular
files, `.` = regular file, `r` = readable. Files sort
lexicographically, so numeric prefixes enforce order.

---

## XDG Conventions

### Foundational rule

The bootstrap `~/.zshenv` unconditionally exports all four XDG
variables before anything else runs. Therefore, **every other file
in the tree uses bare `$XDG_*` variables with no fallbacks**:

```zsh
# CORRECT — everywhere except ~/.zshenv
"$XDG_CONFIG_HOME/foo"
"$XDG_STATE_HOME/zsh/history"

# WRONG — redundant fallback, the variable is guaranteed set
"${XDG_CONFIG_HOME:-$HOME/.config}/foo"
```

### Category semantics (from the XDG spec)

| Variable          | Purpose                           | Example contents                                       |
|-------------------|-----------------------------------|--------------------------------------------------------|
| `XDG_CONFIG_HOME` | User configuration                | `zsh/`, `git/config`, `npm/npmrc`, `p10k/p10k.zsh`    |
| `XDG_DATA_HOME`   | User data / installed artifacts   | `oh-my-zsh/`, `cargo/`, `rustup/`, `gnupg/`           |
| `XDG_CACHE_HOME`  | Regenerable cache                 | `zsh/zcompdump-*`, `npm/`, `go/mod/`                  |
| `XDG_STATE_HOME`  | Persistent but non-portable state | `zsh/history`, `less/history`, `node/node_repl_history`|

**Never cross categories.** Config is not data. History is not
config. Cache is not state.

---

## Directory Structure

```text
~/.zshenv                              ← bootstrap only

~/.config/zsh/
├── .zshenv                            ← defines source_dir, sources zshenv.d/
├── .zprofile                          ← sources zprofile.d/
├── .zshrc                             ← sources zshrc.d/
├── zshenv.d/
│   ├── 00-logging.zsh
│   ├── 05-privacy.zsh
│   ├── 06-xdg-apps.zsh
│   ├── 10-path.zsh
│   └── 11-homebrew.zsh               ← macOS only (chezmoi controls presence)
├── zprofile.d/
│   └── 10-tty-hyprland.zsh           ← Hyprland desktop only (chezmoi controls presence)
└── zshrc.d/
    ├── 01-p10k-instant.zsh
    ├── 10-history.zsh
    ├── 11-keybindings.zsh
    ├── 12-options.zsh
    ├── 20-oh-my-zsh.zsh
    ├── 21-fzf.zsh
    ├── 22-atuin.zsh.disabled
    ├── 23-zoxide.zsh
    ├── 40-aliases.zsh
    ├── 41-functions.zsh
    ├── 50-completions.zsh
    └── 60-p10k-prompt.zsh

~/.config/p10k/p10k.zsh               ← powerlevel10k config
~/.local/share/oh-my-zsh/             ← OMZ (third-party data, NOT config)
~/.local/state/zsh/history             ← shell history
~/.cache/zsh/zcompdump-*              ← completion cache
```

---

## Numbering Convention

Numeric prefixes enforce deterministic load order within each
phase directory.

| Band    | Purpose                          | Examples                                                                   |
|---------|----------------------------------|----------------------------------------------------------------------------|
| `00–09` | Core infrastructure              | `00-logging.zsh`, `05-privacy.zsh`, `06-xdg-apps.zsh`                     |
| `10–19` | Core shell policy / fundamentals | `10-path.zsh`, `10-history.zsh`, `11-keybindings.zsh`, `12-options.zsh`   |
| `20–39` | Frameworks and tool integrations | `20-oh-my-zsh.zsh`, `21-fzf.zsh`, `23-zoxide.zsh`                         |
| `40–69` | Interactive UX                   | `40-aliases.zsh`, `41-functions.zsh`, `50-completions.zsh`, `60-prompt.zsh`|
| `70+`   | Late / optional niceties         | `99-summary.zsh` (optional boot summary)                                   |

**Rules:**

- Numbering reflects dependency flow, not importance
- Do not use late files as band-aids for earlier breakage
- If a framework changes behavior, that framework's file cleans up
  its own side effects

---

## Phase Purity

### `zshenv.d/` — ALL shells

**Allowed:** environment variables, PATH, XDG paths, logging
helpers, privacy flags

**Forbidden:** output, prompts, interactive behavior, subprocesses
in normal operation

### `zprofile.d/` — LOGIN shells only

**Allowed:** session startup, tty gates, agent startup, login-time
actions

### `zshrc.d/` — INTERACTIVE shells only

**Allowed:** shell options, history, aliases, functions, completions,
prompts, framework/plugin integrations

---

## File-by-File Reference

### `zshenv.d/00-logging.zsh`

Diagnostics infrastructure. Defines:

- **`ZSH_BOOT_DEBUG`** — integer flag, default `0`. Set to `1` for
  verbose boot tracing (`ZSH_BOOT_DEBUG=1 zsh`).
- **`_zsh_boot_warnings`** — global array accumulating warnings for
  optional end-of-boot summary.
- **`zlog "msg"`** — prints only when `ZSH_BOOT_DEBUG=1`. Uses
  `print -P` with cyan color. Suppressed during p10k instant prompt.
- **`zwarn "msg"`** — always appends to `_zsh_boot_warnings`. Prints
  to stderr in interactive shells only (yellow). Silent in
  non-interactive contexts to avoid corrupting piped output.
- **`require_cmd name`** — checks `$+commands[name]` (hash table
  lookup, no subprocess). Returns 0 if found, 1 if missing. Calls
  `zwarn` on miss.

```zsh
: ${ZSH_BOOT_DEBUG:=0}
typeset -ga _zsh_boot_warnings

zlog() {
  (( ZSH_BOOT_DEBUG )) || return 0
  [[ -z "${POWERLEVEL9K_INSTANT_PROMPT+x}" ]] || return 0
  print -P "%F{cyan}[zsh]%f $1"
}

zwarn() {
  _zsh_boot_warnings+=("$1")
  [[ -o interactive ]] && print -P "%F{yellow}[zsh warn]%f $1" >&2
}

require_cmd() {
  (( $+commands[$1] )) && return 0
  zwarn "missing: $1"
  return 1
}
```

Typical usage in other scripts:

```zsh
require_cmd fzf || return 0
zlog "init fzf"
```

### `zshenv.d/05-privacy.zsh`

```zsh
export DO_NOT_TRACK=1
```

Respected by Homebrew, Next.js, Gatsby, and other CLI tools per
consoledonottrack.com.

### `zshenv.d/06-xdg-apps.zsh`

Redirects third-party tool directories into XDG-appropriate
locations:

```zsh
# GPG
export GNUPGHOME="$XDG_DATA_HOME/gnupg"

# Rust
export CARGO_HOME="$XDG_DATA_HOME/cargo"
export RUSTUP_HOME="$XDG_DATA_HOME/rustup"

# Go
export GOPATH="$XDG_DATA_HOME/go"
export GOMODCACHE="$XDG_CACHE_HOME/go/mod"

# Node / npm
export NPM_CONFIG_USERCONFIG="$XDG_CONFIG_HOME/npm/npmrc"
export NPM_CONFIG_CACHE="$XDG_CACHE_HOME/npm"
export NODE_REPL_HISTORY="$XDG_STATE_HOME/node/node_repl_history"

# Bun
export BUN_INSTALL="$XDG_DATA_HOME/bun"

# .NET
export DOTNET_CLI_HOME="$XDG_DATA_HOME/dotnet"

# Docker
export DOCKER_CONFIG="$XDG_CONFIG_HOME/docker"

# Less
export LESSHISTFILE="$XDG_STATE_HOME/less/history"

# Wakatime
export WAKATIME_HOME="$XDG_CONFIG_HOME/wakatime"

# SQLite
export SQLITE_HISTORY="$XDG_STATE_HOME/sqlite/history"

# Java
export _JAVA_OPTIONS="-Djava.util.prefs.userRoot=$XDG_CONFIG_HOME/java"

# CMake
export CMAKE_HOME="$XDG_DATA_HOME/cmake"
```

**Maintenance note:** When adding a new redirect here, also add
it to the `xdg_environment` map in `ansible/site.yml` so Ansible
tasks respect the same paths during installation.

### `zshenv.d/10-path.zsh`

```zsh
typeset -U path PATH

[[ -d "$HOME/.local/bin" ]] && path=("$HOME/.local/bin" "${path[@]}")
[[ -d "$CARGO_HOME/bin" ]] && path=("$CARGO_HOME/bin" "${path[@]}")
[[ -d "$GOPATH/bin" ]] && path=("$GOPATH/bin" "${path[@]}")
[[ -d "$BUN_INSTALL/bin" ]] && path=("$BUN_INSTALL/bin" "${path[@]}")
[[ -d "$DOTNET_CLI_HOME/tools" ]] && path=("$DOTNET_CLI_HOME/tools" "${path[@]}")

export PATH
```

`typeset -U` deduplicates PATH entries. Every path is guarded with
`[[ -d ]]` so missing tools produce no dead entries.

### `zshenv.d/11-homebrew.zsh` (macOS only)

```zsh
if [[ -x /opt/homebrew/bin/brew ]]; then
  eval "$(/opt/homebrew/bin/brew shellenv)"
elif [[ -x /usr/local/bin/brew ]]; then
  eval "$(/usr/local/bin/brew shellenv)"
fi
```

Handles Apple Silicon (`/opt/homebrew`) and Intel (`/usr/local`).
Chezmoi excludes this file on non-Darwin hosts via
`.chezmoiignore`.

### `zprofile.d/10-tty-hyprland.zsh`

```zsh
[[ -o interactive ]] || return 0
[[ -z "$SSH_CONNECTION" ]] || return 0
[[ "$(tty)" == /dev/tty1 ]] || return 0

if command -v uwsm &>/dev/null; then
  exec uwsm start hyprland-uwsm.desktop
fi
```

Offers Hyprland launch on tty1 only. Guards: interactive check,
SSH rejection, tty1 gate. Chezmoi excludes this on any host where
`.desktop != "hyprland"` via `.chezmoiignore`.

### `zshrc.d/01-p10k-instant.zsh`

```zsh
if [[ -r "$XDG_CACHE_HOME/p10k-instant-prompt-${(%):-%n}.zsh" ]]; then
  source "$XDG_CACHE_HOME/p10k-instant-prompt-${(%):-%n}.zsh"
fi
```

Must run before any console output. Numbered `01` — after
`00-logging.zsh` (which is silent when debug is off) but before
everything else.

**Constraint:** no script between `01` and `20` (when p10k fully
initializes via OMZ) may produce console output.

### `zshrc.d/10-history.zsh`

```zsh
[[ -d "$XDG_STATE_HOME/zsh" ]] || mkdir -p "$XDG_STATE_HOME/zsh"

HISTFILE="$XDG_STATE_HOME/zsh/history"
HISTSIZE=100000
SAVEHIST=100000

setopt inc_append_history
setopt hist_ignore_dups
setopt hist_ignore_all_dups
setopt hist_save_no_dups
setopt hist_reduce_blanks
setopt hist_ignore_space
setopt hist_no_store

zshaddhistory() {
  whence ${${(z)1}[1]} >| /dev/null || return 1
}
```

History is **state** per the XDG spec. The `zshaddhistory` hook
skips entries whose first word is not a known command.

### `zshrc.d/11-keybindings.zsh`

```zsh
bindkey -v
```

Vi mode.

### `zshrc.d/12-options.zsh`

```zsh
setopt auto_cd
```

### `zshrc.d/20-oh-my-zsh.zsh`

```zsh
export ZSH="$XDG_DATA_HOME/oh-my-zsh"

if [[ ! -d "$ZSH" ]]; then
  zwarn "oh-my-zsh not installed at $ZSH"
  return 0
fi

ZSH_THEME="powerlevel10k/powerlevel10k"
COMPLETION_WAITING_DOTS="true"
zstyle ':omz:update' mode auto

plugins=(git sudo)

source "$ZSH/oh-my-zsh.sh"

# --- OMZ side-effect corrections ---
unsetopt share_history
setopt inc_append_history

zlog "oh-my-zsh loaded, side effects corrected"
```

**Key decisions:**

- OMZ lives in `XDG_DATA_HOME` (third-party data, not config)
- p10k lives at `$ZSH/custom/themes/powerlevel10k` — inside OMZ's
  custom directory so OMZ's auto-updater manages both lifecycles
- Side effects corrected in the same file that causes them — never
  in a separate late file

### `zshrc.d/21-fzf.zsh`

```zsh
require_cmd fzf || return 0
zlog "init fzf"
source <(fzf --zsh)
```

### `zshrc.d/23-zoxide.zsh`

```zsh
require_cmd zoxide || return 0
zlog "init zoxide"
eval "$(zoxide init zsh)"
```

### `zshrc.d/40-aliases.zsh`

```zsh
if require_cmd eza; then
  alias ls='eza -lha --icons --no-user --git --no-permissions --sort=name'
fi

if require_cmd fd && require_cmd fzf-tmux && require_cmd nvim; then
  alias v='fd --type f --hidden --exclude .git | fzf-tmux -p | xargs -r nvim'
fi

if require_cmd nvim; then
  alias vim='nvim'
fi

alias ..='cd ..'
alias ...='cd ../..'
```

### `zshrc.d/41-functions.zsh`

```zsh
if require_cmd fzf; then
  fcd() {
    local dir
    dir=$(find "${1:-.}" -type d -not -path '*/.*' 2>/dev/null | fzf +m) &&
      cd "$dir"
  }
fi
```

### `zshrc.d/50-completions.zsh`

```zsh
[[ -d "$XDG_CACHE_HOME/zsh" ]] || mkdir -p "$XDG_CACHE_HOME/zsh"

autoload -Uz compinit
compinit -d "$XDG_CACHE_HOME/zsh/zcompdump-${ZSH_VERSION}"

zlog "completions loaded"
```

### `zshrc.d/60-p10k-prompt.zsh`

```zsh
if [[ -r "$XDG_CONFIG_HOME/p10k/p10k.zsh" ]]; then
  source "$XDG_CONFIG_HOME/p10k/p10k.zsh"
fi
```

---

## Per-Host File Presence

Chezmoi controls which files exist on each host via
`.chezmoiignore`, using three dimensions from `.chezmoi.toml.tmpl`:

| Dimension   | Values                      | Controls                                             |
|-------------|-----------------------------|------------------------------------------------------|
| `.chezmoi.os` | `darwin`, `linux`         | OS-specific scripts (Homebrew, Linux-only tools)     |
| `.desktop`  | `hyprland`, `none`          | Desktop vs CLI/server, compositor-specific configs    |
| `.profile`  | `work`, `personal`          | Corporate vs personal tool configs                   |

**If a file is deployed, it runs unconditionally.** No inline OS
detection or hostname checks in shell scripts. All gating happens
in `.chezmoiignore`. See `workstation-bootstrap.md` for the full
`.chezmoiignore` reference and gating matrix.

---

## Separation of Concerns Rules

1. **Canonical policy lives in dedicated core scripts.**
   `10-history.zsh` defines history behavior.

2. **Framework side effects are corrected in the framework's file.**
   `20-oh-my-zsh.zsh` loads OMZ then immediately unsets
   `share_history`. If OMZ is removed, its compensation logic is
   deleted with it.

3. **Never use a late file to repair an early file.** No
   `90-history-fix.zsh`. Cause and correction must be colocated.

4. **Aliases stay in `40-aliases.zsh`** even if they compose
   multiple tools. If something becomes complex enough to need
   logic, it graduates to `41-functions.zsh`.

5. **Chezmoi controls per-host file presence.** If a script exists
   on a host, it should run unconditionally. Avoid inline OS
   detection sprawl. The `.chezmoiignore` file gates host-specific
   scripts using `.chezmoi.os`, `.desktop`, and `.profile`
   dimensions. See `workstation-bootstrap.md`.

---

## Fail-Open Behavior

- `require_cmd tool || return 0` — missing tools skip cleanly,
  never crash the shell
- `zwarn` collects warnings silently in non-interactive shells,
  prints to stderr in interactive
- Every tool integration script checks for its dependency before
  initializing
- Shell startup completes successfully even if every optional tool
  is missing

---

## File Deprecation Convention

Rename the extension to disable a file:

```text
22-atuin.zsh.disabled     ← ignored by *.zsh glob
40-aliases.zsh.bak        ← ignored
40-aliases.zsh.deprecated ← ignored
```

No loader changes required. Any file not ending in `.zsh` is
invisible.

---

## Common Zsh Tasks

| Task | How |
|---|---|
| Add a new tool integration | Create `zshrc.d/2x-toolname.zsh`, guard with `require_cmd`, add package to Ansible (see `workstation-bootstrap.md`) |
| Add a new env var redirect | Add export to `06-xdg-apps.zsh`, mirror in Ansible `xdg_environment`, update `10-path.zsh` only if the tool has a `bin/` dir |
| Replace OMZ with zinit | Delete `20-oh-my-zsh.zsh`, create `20-zinit.zsh`, remove OMZ Ansible tasks, add zinit init |
| Disable a script temporarily | Rename: `mv 22-atuin.zsh 22-atuin.zsh.disabled` |
| Debug slow startup | `ZSH_BOOT_DEBUG=1 zsh` |
| Add a host-specific zsh file | Create the file in chezmoi source, add a gating block in `.chezmoiignore` using `.desktop`, `.profile`, `.chezmoi.os`, or `.hostname` |
