# Workstation Bootstrap

## Overview

Two tools with strict separation:

| Tool        | Responsibility                                              |
| ----------- | ----------------------------------------------------------- |
| **Chezmoi** | Dotfile deployment, templating, per-host file gating        |
| **Ansible** | Package installation, infrastructure, service configuration |

They do not overlap. Chezmoi never installs packages. Ansible never touches dotfile contents.

## Bootstrap Commands

| Platform | Command                                                                   |
| -------- | ------------------------------------------------------------------------- |
| Arch     | `sudo pacman -S --needed git chezmoi && chezmoi init --apply PixelHabits` |
| macOS    | `brew install chezmoi && chezmoi init --apply PixelHabits`                |
| Ubuntu   | `sudo apt install git chezmoi && chezmoi init --apply PixelHabits`        |

Chezmoi prompts for identity, deploys dotfiles, then automatically runs Ansible.

## Machine Identity

Set during `chezmoi init`, stored in `~/.config/chezmoi/chezmoi.toml`:

| Field         | Values                       | Purpose                       |
| ------------- | ---------------------------- | ----------------------------- |
| `osid`        | arch, ubuntu, fedora, darwin | Distro-specific packages      |
| `desktop`     | hyprland, none               | Desktop vs CLI/server gating  |
| `form_factor` | laptop, desktop, server      | Hardware-specific tasks       |
| `profile`     | work, personal               | Corporate vs personal configs |

Re-prompt: `chezmoi init --prompt`

## Gating Matrix

| Machine Type       | desktop  | form_factor | profile  | Gets                          |
| ------------------ | -------- | ----------- | -------- | ----------------------------- |
| Work Arch laptop   | hyprland | laptop      | work     | Full desktop + work configs   |
| Home gaming PC     | hyprland | desktop     | personal | Full desktop + gaming configs |
| Work Ubuntu server | none     | server      | work     | CLI only + work configs       |
| Personal Mac       | none     | laptop      | personal | CLI + Homebrew                |

## Ansible Architecture

**Execution order:**

```
pre_tasks: validate OS, detect bare metal, detect Nvidia GPU
roles:
  1. base     <- XDG dirs, yay bootstrap, package installation
  2. zsh      <- default shell, omz, p10k
  3. battery  <- charge threshold service (laptop only)
  4. hyprland <- compositor, desktop apps (Arch + desktop only)
  5. dev      <- rust toolchain, node LTS (desktop only)
```

**Tags:**
| Command | What runs |
|--------------------------------------|---------------------------------|
| `ansible-playbook site.yml` | Everything |
| `--tags cli` | base + zsh + battery on laptops |
| `--tags desktop` | hyprland role only |

## Separation of Concerns

| Concern                    | Owner                        |
| -------------------------- | ---------------------------- |
| Machine identity           | chezmoi `.chezmoi.toml.tmpl` |
| Which files exist per host | chezmoi `.chezmoiignore`     |
| Dotfile contents           | chezmoi source files         |
| Package installation       | Ansible                      |
| Hardware-specific tasks    | Ansible via `form_factor`    |
| Nvidia driver selection    | Ansible `site.yml` pre_tasks |
| Shell runtime behavior     | zsh drop-in dirs             |

## Package Organization

Packages are defined in `ansible/site.yml`:

- `common_packages` — installed everywhere
- `distro_packages` — platform-specific (Archlinux, Ubuntu, Darwin, etc.)
- `hardware_packages` — bare-metal only (filesystem tools, fwupd)
- `aur_packages` — AUR-only packages (neovim-git, nvidia drivers)
- `macos_casks` — macOS GUI apps

Nvidia packages are dynamically appended based on GPU detection.

## Common Tasks

| Task                    | How                                                                                |
| ----------------------- | ---------------------------------------------------------------------------------- |
| Add CLI tool            | Add to `common_packages` or `distro_packages`                                      |
| Add AUR package         | Add to `aur_packages`                                                              |
| Add macOS cask          | Add to `macos_casks`                                                               |
| Add XDG redirect        | Add to `06-xdg-apps.zsh` AND `site.yml` xdg_environment                            |
| Re-run Ansible manually | `cd ~/.local/share/chezmoi/ansible && ansible-playbook site.yml --ask-become-pass` |
| Add host-specific file  | Create file, add gating in `.chezmoiignore`                                        |

## Chezmoi Gating

`.chezmoiignore` uses three dimensions for file gating:

```
# OS gating
{{- if ne .chezmoi.os "darwin" }}
dot_config/zsh/zshenv.d/11-homebrew.zsh
{{- end }}

# Desktop gating
{{- if ne .desktop "hyprland" }}
dot_config/hypr/
dot_config/waybar/
{{- end }}

# Profile gating
{{- if ne .profile "work" }}
dot_config/git/config-work
{{- end }}
```

**Rule:** If a file is deployed, it runs unconditionally. All conditional logic lives in `.chezmoiignore`, not inline in scripts.

## Ansible Trigger Mechanism

`run_onchange_after_ansible.sh.tmpl` contains hash comments for each Ansible file:

```bash
# site.yml hash: {{ include "ansible/site.yml" | sha256sum }}
```

When any included file changes, the rendered script changes, triggering chezmoi to re-run Ansible. Dotfile-only edits do not trigger Ansible.

## Constraints

1. `ansible/` is in `.chezmoiignore` — never deployed to $HOME
2. No inventory file — `connection: local` on the play
3. Homebrew is a user prerequisite on macOS, not managed by Ansible
4. `xdg_environment` in site.yml must stay in sync with `06-xdg-apps.zsh`
5. The `run_onchange_` script re-runs Ansible only when Ansible files change
