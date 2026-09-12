# Workstation Bootstrap

## Overview

Two tools with strict separation:

| Tool        | Responsibility                                              |
| ----------- | ----------------------------------------------------------- |
| **Chezmoi** | Dotfile deployment, templating, per-host file gating        |
| **Ansible** | Package installation, infrastructure, service configuration |

They do not overlap. Chezmoi never installs packages. Ansible never touches dotfile contents.

## Bootstrap Commands

Follow [Git worktrees and chezmoi](worktrees.md) for installation and initial setup.
Select a worktree as the chezmoi source before you deploy files.

On Arch, Ansible prompts to update pacman repositories with the CachyOS repo
script when CachyOS repositories are missing. The interactive task runs the same
script as:

```bash
curl -O https://mirror.cachyos.org/cachyos-repo.tar.xz
tar xvf cachyos-repo.tar.xz
cd cachyos-repo
sudo ./cachyos-repo.sh
cd ..
```

Chezmoi prompts for identity, deploys dotfiles, then automatically runs Ansible.

## Machine Identity

Set during `chezmoi init`, stored in `~/.config/chezmoi/chezmoi.toml`:

| Field         | Values                       | Purpose                       |
| ------------- | ---------------------------- | ----------------------------- |
| `osid`        | arch, ubuntu, fedora, darwin | Distro-specific packages      |
| `desktop`     | hyprland, none               | Desktop vs CLI/server gating  |
| `form_factor` | laptop, desktop, server      | Hardware-specific tasks       |
| `profile`     | work, personal               | Corporate vs personal configs |

To change machine choices, run `chezmoi init --prompt` from a source with the current template.
Do not reinitialize the preserved `dev` snapshot. See [source selection](worktrees.md#select-the-live-source).

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
  1. base     <- XDG dirs, CachyOS repo check, package installation
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
- `macos_casks` — macOS GUI apps

Nvidia packages are dynamically appended to the Arch pacman package set based on
GPU detection. AUR packages are intentionally not automated; install them
manually after reviewing the PKGBUILD.

## Common Tasks

| Task                    | How                                                                                |
| ----------------------- | ---------------------------------------------------------------------------------- |
| Add CLI tool            | Add to `common_packages` or `distro_packages`                                      |
| Add repo package        | Add to `common_packages`, `distro_packages`, or the relevant role package list      |
| Add AUR package         | Install manually after reviewing the PKGBUILD                                      |
| Add macOS cask          | Add to `macos_casks`                                                               |
| Add XDG redirect        | Add absolute path to `environment.d/10-xdg.conf`; mirror as `${VAR:-/absolute/path}` fallback in `06-xdg-apps.zsh`; update `site.yml` only if Ansible needs it |
| Re-run Ansible manually | `cd "$(chezmoi execute-template '{{ .chezmoi.sourceDir }}')/ansible" && ansible-playbook site.yml --ask-become-pass` |
| Add host-specific file  | Create file, add gating in `.chezmoiignore`                                        |

## Chezmoi Gating

`.chezmoiignore` uses three dimensions for file gating:

```
# OS gating
{{- if ne .chezmoi.os "darwin" }}
.config/zsh/zshenv.d/11-homebrew.zsh
{{- end }}

# Desktop gating
{{- if ne .desktop "hyprland" }}
.config/hypr/
.config/waybar/
{{- end }}

# Profile gating
{{- if ne .profile "work" }}
.config/git/config-work
{{- end }}
```

**Rule:** If a file is deployed, it runs unconditionally. All conditional logic lives in `.chezmoiignore`, not inline in scripts.

## Ansible Trigger Mechanism

`run_onchange_after_ansible.sh.tmpl` contains hash comments for each Ansible file:

```bash
# site.yml hash: {{ include "ansible/site.yml" | sha256sum }}
```

When any included file changes, the rendered script changes, triggering chezmoi to re-run Ansible. Dotfile-only edits do not trigger Ansible when the source path stays the same.
Changing the source worktree also changes the script and can trigger Ansible.

## Constraints

1. `ansible/` is in `.chezmoiignore` — never deployed to $HOME
2. No inventory file — `connection: local` on the play
3. Homebrew is a user prerequisite on macOS, not managed by Ansible
4. `environment.d/10-xdg.conf` is primary; `06-xdg-apps.zsh` only fills unset values; `xdg_environment` is an Ansible-only subset
5. The `run_onchange_` script runs again when its rendered contents change, including its source path
