# Coding Standards & Conventions

## Git Worktrees

- Layout: repo container `.bare/`, `main/`, `dev/`, feature dirs. Container not chezmoi source.
- `main`: remote baseline plus reviewed commits. `dev`: preserved uncommitted WIP. Feature branches: scoped changes + PRs.
- Preserve `dev` files/index. No stash, reset, clean, commit, or bulk copy into feature branch without user request.
- Run Git from chosen worktree: `git -C <worktree> ...`. Repo admin: `git --git-dir=<container>/.bare ...`.
- Chezmoi source = local config `sourceDir`. `cd` does not switch source. Always pass `chezmoi --source <worktree>` for feature commands.
- Default stable source: `main`. This machine can select `dev` explicitly. Never assume active source.
- Inspect source: `chezmoi execute-template '{{ .chezmoi.sourceDir }}'`.
- `.chezmoi.toml.tmpl` preserves selected source on init. Old `dev` snapshot predates fix: avoid re-init there.
- Worktrees share destination HOME and chezmoi state. Feature `apply` changes live files; review scoped diff first.
- Ansible run-onchange includes source path. Worktree switch can trigger provisioning. For dotfile-only apply, pass exact targets + `--exclude scripts`.
- New machine: follow `worktrees.md`. No `chezmoi init <repo>` into container.
- Human docs: plain English. Agent instructions: terse, exact. Keep commands literal.

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
