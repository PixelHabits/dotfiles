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

### PWA Apps
- Catalog: `.chezmoidata/pwa.toml`. Machine choices: `mail_provider`, `linear_url` in local chezmoi `[data]`.
- Resolver: `.chezmoitemplates/pwa-apps.json`. Hyprland bindings/rules + Waybar icons consume same result.
- Provider URL + class travel together. Match domain + any app path/profile. Do not embed account slugs in rules.
- Keep named workspace IDs stable. App launch uses Chromium `--app`, current `$browser` profile.
- Gate helper + desktop files in `.chezmoiignore`. No desktop checks inside helper.
- Run `python3 tests/pwa.py`. Tests use temp files + fake desktop commands; no live apply.

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
1. Add absolute tool path under `[apps]` in `.chezmoitemplates/xdg-env.toml.tmpl`.
2. `.config/zsh/.zshenv` renders `[base]`, `zshenv.d/06-xdg-apps.zsh` renders `[apps]`, `environment.d/10-xdg.conf` renders both. Shell keeps existing values.
3. Bootstrap `~/.zshenv` only locates ZDOTDIR. Full zshenv sets base defaults before drop-ins, including inherited-ZDOTDIR starts.
4. Add to `xdg_environment` in `ansible/site.yml` only when Ansible invokes that tool.
5. If tool has `bin/`, add PATH entry in `zshenv.d/10-path.zsh`.
6. Validate: `uv run tests/xdg/test_defaults.py`. Temporary homes only; no live apply or SSH/macOS runtime claim.

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

## Codex

- Shared keys: `.chezmoitemplates/codex/shared.toml.tmpl`. `modify_private_config.toml` merges them over the destination. Codex runtime writes (trust, notices, plugin state) stay local, never in Git.
- Shared MCP servers replace the destination table whole. Local-only servers survive.
- Stdio MCP servers get a fixed env whitelist from Codex. Forward XDG names with `env_vars`; never inline absolute paths.
- No trusted parent roots. No credentials, sessions, databases, or profile files in Git. No `chezmoi add/re-add` of Codex config.
- Codex home env: `.chezmoitemplates/codex/home-env.toml.tmpl` renders `environment.d/22-codex.conf` and `zshenv.d/20-codex.zsh`. Dev-gate config and redirects together.
- Tests: `uv run tests/codex/test_config.py`. Python >=3.14 via PEP 723; temporary HOME only; no credentials or external MCP servers.
- Human guide: `codex.md`.

## Hyprland Recovery

- Evidence + hardware test limits: `suspend-recovery.md`.
- Monitor values: `.chezmoidata/hyprland.toml`; local override: `data.hyprland.monitors`.
- No live suspend, lock, session activation, GPU changes, or helper execution during tests.
- Mock tests: `uv run tests/test_hypr_rescue.py`.
- Render tests: `uv run tests/test_suspend_templates.py`. Uses temporary config; Hyprland parse-only when available.
- Driver workaround != verified fix. Preserve lock process; never select another user's session.
