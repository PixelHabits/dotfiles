# Coding Standards & Conventions

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
- `aur_packages` — AUR only (dynamically extended for Nvidia)
- `macos_casks` — macOS GUI apps

## Chezmoi

### Templates
- Use `.tmpl` suffix for templated files
- Access data via `.chezmoi.os`, `.desktop`, `.profile`, `.osid`
- Gating logic lives in `.chezmoiignore`, not inline in scripts

### Gating Hierarchy
Prefer: `profile` > `desktop` > `os` > `hostname`

```
# .chezmoiignore example
{{- if ne .desktop "hyprland" }}
dot_config/hypr/
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
1. Add export to `zshenv.d/06-xdg-apps.zsh`
2. Add to `xdg_environment` in `ansible/site.yml`
3. If tool has `bin/`, add PATH entry in `zshenv.d/10-path.zsh`

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
