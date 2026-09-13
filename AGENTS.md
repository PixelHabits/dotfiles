# Coding Standards & Conventions

## Git Worktrees

- Layout: repo container `.bare/`, `main/`, `dev/`, feature dirs. Container not chezmoi source.
- `main`: stable branch. `dev`: development branch. Feature branches: scoped changes + PRs.
- Preserve existing user changes in every worktree. Stage only task-related paths or hunks.
- Run Git from chosen worktree: `git -C <worktree> ...`. Repo admin: `git --git-dir=<container>/.bare ...`.
- Chezmoi source = local config `sourceDir`. `cd` does not switch source. Always pass `chezmoi --source <worktree>` for feature commands.
- Select `main` for stable config or `dev` for development config. Never assume active source.
- Inspect source: `chezmoi execute-template '{{ .chezmoi.sourceDir }}'`.
- `.chezmoi.toml.tmpl` preserves selected source on init.
- Worktrees share destination HOME and chezmoi state. Feature `apply` changes live files; review scoped diff first.
- Ansible run-onchange includes source path. Worktree switch can trigger provisioning. For dotfile-only apply, pass exact targets + `--exclude scripts`.
- New machine: follow `worktrees.md`. No `chezmoi init <repo>` into container.
- Human docs: plain English. Agent instructions: terse, exact. Keep commands literal.

## Claude Code

- Human guide: `claude.md`. Dev machines only; gate paths in `.chezmoiignore`.
- Shared config: `.config/claude`. Runtime: `.local/state/claude`; config symlinks only.
- Runtime auth/history/plugins stay local. Never import runtime directory into source.
- `modify_private_settings.json`: preserve local keys; manage attribution, `refs` hooks, `env.CLAUDE_BASH_MAINTAIN_PROJECT_WORKING_DIR`, and `permissions.deny` `EnterWorktree`.
- Launcher `dot_local/bin/executable_claude`: names project store with 31char sanitized repo basename + 32hex Git digest of canonical common-dir path (`CLAUDE_CODE_PROJECT_DIR_NAME`). Name <=64 chars. Same repo worktrees share; unrelated paths differ. Valid local `.bare` wins over outer repo. Explicit name wins. Hash writes no object. Exec next `claude` on PATH. Container `CLAUDE.md` = `@AGENTS.md`, untracked. Validate: `python3 tests/test_launcher.py`.
- Claude redirects: dedicated `environment.d/20-claude.conf` + `zshenv.d/21-claude.zsh` for dev gating.
- Claude scratch: `.local/state/claude/tmp`; active work, user-cleans. No automatic deletion or global `TMPDIR`.
- Claude tool shell: `/bin/bash`; interactive shell unchanged. Inherited XDG exports survive shell change.
- Memory directory: per project only. No global project-name override, auto-sync hook, or company memory in public repo.
- Preserve privacy opt-outs. No bypass alias. No guessed settings keys.
- Validate: `uv run tests/test_claude_config.py`.

## Agent Instructions

- Shared core: `dot_config/agents/AGENTS.md`. One file for every agent. Invariants only: no versions, PR numbers, or dates.
- Claude: `dot_config/claude/CLAUDE.md` = `@~/.config/agents/AGENTS.md` import + Claude-only appendix. Codex: `.config/codex/AGENTS.md` symlink to the core.
- Skills: `dot_agents/skills/<name>/SKILL.md`, agentskills layout, read by Claude, Codex, pi. Domain detail lives here, loaded on demand. Field-note skills read as history, not law.
- Guard: `uv run tests/test_agent_instructions.py` (import line, size budget, frontmatter, stale-token lint).

## Shell Scripts (zsh)

### Patterns
```zsh
# Guard with require_cmd — fail open, never crash
require_cmd fzf || return 0

# Log for debugging (silent unless ZSH_BOOT_DEBUG=1)
zlog "init fzf"

# Warn on issues (always recorded, printed in interactive shells)
zwarn "missing: $tool"
```

### File Naming
- Drop-in scripts: `NN-name.zsh` where NN is the load order (00-99)
- Disabled scripts: rename to `.zsh.disabled`
- Never cross phase boundaries (zshenv.d scripts can't use interactive features)

## Ansible
### Patterns
```yaml
# Guard tasks with when conditions
- name: Skip on non-Arch systems
  ansible.builtin.meta: end_role
  when: ansible_distribution != 'Archlinux'

# Use become only where needed
- name: Install packages
  become: true
  community.general.pacman:
    name: "{{ packages }}"
```

### Package Organization
- `common_packages` — all platforms
- `distro_packages[Archlinux|Ubuntu|Darwin]` — platform-specific
- `macos_casks` — macOS GUI apps

## Chezmoi

### Templates
- Use `.tmpl` suffix for templated files
- Access data via `.chezmoi.os`, `.desktop`, `.form_factor`, `.profile`, `.dev`, `.osid`
- Gating logic lives in `.chezmoiignore`, not inline in scripts

### Gating Hierarchy
Prefer: `profile` > `dev` > `desktop` > `os` > `hostname`

```
# .chezmoiignore example
{{- if ne .desktop "hyprland" }}
.config/hypr/
{{- end }}
```

## XDG Compliance

### Category Rules
| Variable          | Use for                    | Never for              |
|-------------------|----------------------------|------------------------|
| `XDG_CONFIG_HOME` | User configuration         | Data, cache, state     |
| `XDG_DATA_HOME`   | Installed artifacts        | Config, cache, state   |
| `XDG_CACHE_HOME`  | Regenerable cache          | Config, data, state    |
| `XDG_STATE_HOME`  | Persistent non-config      | Config, data, cache    |

### Adding a New XDG Redirect
1. Add absolute path to `environment.d/10-xdg.conf` as the primary runtime value
2. Add matching fallback to `zshenv.d/06-xdg-apps.zsh` using `${VAR:-/absolute/path}`
3. Add to `xdg_environment` in `ansible/site.yml` only when Ansible invokes that tool
4. If tool has `bin/`, add PATH entry in `zshenv.d/10-path.zsh`

## Documentation

### What to Document
- Architectural decisions and their rationale
- Non-obvious patterns and conventions
- Gating matrices and separation of concerns
- Common tasks as quick-reference tables

### What NOT to Document
- Line-by-line code explanations (code should be self-documenting)
- Full file contents (reference the actual files)
- Traces/examples that duplicate code behavior

## Commit Messages

Follow conventional commits:
- `feat(scope):` new feature
- `fix(scope):` bug fix
- `docs(scope):` documentation only
- `refactor(scope):` code change that neither fixes a bug nor adds a feature
- `chore(scope):` maintenance tasks

## Testing Changes

```bash
# Debug zsh startup
ZSH_BOOT_DEBUG=1 zsh

# Dry-run chezmoi
chezmoi diff

# Test Ansible syntax
ansible-playbook site.yml --syntax-check

# Run specific Ansible tags
ansible-playbook site.yml --tags cli --ask-become-pass
```
