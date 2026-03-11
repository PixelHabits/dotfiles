# Workstation Bootstrap — Chezmoi + Ansible

## Purpose

This document describes how machines are bootstrapped from scratch:
chezmoi deployment, machine configuration, Ansible playbook
architecture, package management, Nvidia GPU detection, and
per-host configuration.

For zsh shell behavior, boot chain, and drop-in script reference,
see `zsh-dotfile-architecture.md`.

---

## System Overview

Two tools, strict separation:

| Tool | Responsibility |
|---|---|
| **chezmoi** | Dotfile version control, templating, deployment, per-host file presence via `.chezmoiignore`, machine identity via `.chezmoi.toml.tmpl` |
| **Ansible** | Package installation, infrastructure setup (yay), service configuration, repo cloning (OMZ, p10k) |

**They do not overlap.** Chezmoi never installs packages. Ansible
never touches dotfile contents. The connection point is a chezmoi
`run_onchange_` script that invokes Ansible after dotfile
deployment and re-runs whenever Ansible files change.

---

## Target Platforms

| Platform | Role | Status |
|---|---|---|
| Arch Linux | Desktop workstation or SSH server | Active, fully tested |
| macOS / Darwin | Desktop (always desktop, never headless) | Active |
| Ubuntu | SSH servers, headless boxes | Framework ready, needs package validation |
| Fedora | Future | Framework ready, needs package validation |

**Ubuntu/Fedora note:** `common_packages` entries like `bottom`,
`eza`, `rustup`, and `fnm` may not exist in default repos.
Validate and add PPAs/copr repos when activating those platforms.

---

## Machine Identity

Chezmoi prompts for machine-specific data during `chezmoi init`
and persists it in `~/.config/chezmoi/chezmoi.toml`. These values
drive `.chezmoiignore` gating and the Ansible run script.

### `.chezmoi.toml.tmpl`

```toml
{{- $osid := .chezmoi.os -}}
{{- if hasKey .chezmoi "osRelease" -}}
{{-   if hasKey .chezmoi.osRelease "id" -}}
{{-     $osid = .chezmoi.osRelease.id -}}
{{-   end -}}
{{- end -}}

{{- $email := promptStringOnce . "email" "Email address" -}}
{{- $desktop := promptStringOnce . "desktop" "Desktop environment (hyprland/none)" -}}
{{- $profile := promptStringOnce . "profile" "Machine profile (work/personal)" -}}

[data]
  osid = {{ $osid | quote }}
  hostname = {{ .chezmoi.hostname | quote }}
  email = {{ $email | quote }}
  desktop = {{ $desktop | quote }}
  profile = {{ $profile | quote }}
```

| Field | Source | Values | Purpose |
|---|---|---|---|
| `osid` | Auto-detected | `arch`, `ubuntu`, `fedora`, `darwin` | Distro-specific Ansible install commands |
| `hostname` | Auto-detected | Machine hostname | Host-gated files (use sparingly) |
| `email` | User prompt | Any email | Git config, tool registration |
| `desktop` | User prompt | `hyprland`, `none` | Desktop vs CLI gating |
| `profile` | User prompt | `work`, `personal` | Corporate vs personal tool configs |

To re-prompt all values: `chezmoi init --prompt`

---

## Bootstrap — Two Commands

| Platform | Commands |
|---|---|
| Arch | `sudo pacman -S --needed git chezmoi && chezmoi init --apply PixelHabits` |
| macOS | `brew install chezmoi && chezmoi init --apply PixelHabits` |
| Ubuntu | `sudo apt install git chezmoi && chezmoi init --apply PixelHabits` |

Chezmoi prompts for `email`, `desktop`, and `profile` during
`chezmoi init`. It then deploys dotfiles and
`run_onchange_after_ansible.sh.tmpl` installs Ansible and runs
the playbook automatically.

---

## Repository Layout (chezmoi source)

```text
~/.local/share/chezmoi/
├── .chezmoi.toml.tmpl
├── .chezmoiignore
├── run_onchange_after_ansible.sh.tmpl
├── dot_zshenv
├── dot_config/
│   ├── zsh/
│   │   ├── dot_zshenv
│   │   ├── dot_zprofile
│   │   ├── dot_zshrc
│   │   ├── zshenv.d/
│   │   │   ├── 00-logging.zsh
│   │   │   ├── 05-privacy.zsh
│   │   │   ├── 06-xdg-apps.zsh
│   │   │   ├── 10-path.zsh
│   │   │   └── 11-homebrew.zsh
│   │   ├── zprofile.d/
│   │   │   └── 10-tty-hyprland.zsh
│   │   └── zshrc.d/
│   │       ├── 01-p10k-instant.zsh
│   │       ├── 10-history.zsh
│   │       ├── 11-keybindings.zsh
│   │       ├── 12-options.zsh
│   │       ├── 20-oh-my-zsh.zsh
│   │       ├── 21-fzf.zsh
│   │       ├── 22-atuin.zsh.disabled
│   │       ├── 23-zoxide.zsh
│   │       ├── 40-aliases.zsh
│   │       ├── 41-functions.zsh
│   │       ├── 50-completions.zsh
│   │       └── 60-p10k-prompt.zsh
│   └── p10k/
│       └── p10k.zsh
├── ansible/
│   ├── site.yml
│   ├── files/
│   │   └── ghostty.terminfo
│   └── roles/
│       ├── base/
│       │   └── tasks/
│       │       ├── main.yml
│       │       ├── arch.yml
│       │       └── ubuntu.yml
│       ├── zsh/
│       │   └── tasks/
│       │       └── main.yml
│       ├── dev/
│       │   └── tasks/
│       │       └── main.yml
│       └── hyprland/
│           └── tasks/
│               └── main.yml
├── README.md
├── zsh-dotfile-architecture.md
└── workstation-bootstrap.md
```

---

## Deployed Layout (what ends up on the machine)

```text
~/.zshenv

~/.config/
├── chezmoi/chezmoi.toml               ← generated from .chezmoi.toml.tmpl
├── zsh/
│   ├── .zshenv
│   ├── .zprofile
│   ├── .zshrc
│   ├── zshenv.d/*.zsh
│   ├── zprofile.d/*.zsh
│   └── zshrc.d/*.zsh
└── p10k/p10k.zsh

~/.local/share/
├── oh-my-zsh/                     ← Ansible clones
│   └── custom/themes/powerlevel10k/
├── cargo/                         ← rustup respects XDG
├── rustup/
└── chezmoi/                       ← chezmoi source repo

~/.local/state/zsh/history         ← Ansible creates dir
~/.cache/zsh/zcompdump-*           ← Ansible creates dir
```

---

## Chezmoi Configuration

### `.chezmoiignore`

Controls which files are deployed per host using three dimensions:
OS, desktop environment, and machine profile.

```text
# ════════════════════════════════════════════════════════════
# Source-only files — never deployed to $HOME
# ════════════════════════════════════════════════════════════
ansible/
README.md
zsh-dotfile-architecture.md
workstation-bootstrap.md

# ════════════════════════════════════════════════════════════
# OS-gated files
# ════════════════════════════════════════════════════════════

# ── macOS only ──────────────────────────────────────────────
{{- if ne .chezmoi.os "darwin" }}
dot_config/zsh/zshenv.d/11-homebrew.zsh
# dot_config/zsh/zshrc.d/42-macos-aliases.zsh
{{- end }}

# ── Linux only ──────────────────────────────────────────────
{{- if ne .chezmoi.os "linux" }}
# dot_config/zsh/zshrc.d/42-linux-aliases.zsh
# dot_config/zsh/zshrc.d/24-docker.zsh
{{- end }}

# ════════════════════════════════════════════════════════════
# Desktop-gated files
# ════════════════════════════════════════════════════════════

# ── Hyprland desktop only ───────────────────────────────────
{{- if ne .desktop "hyprland" }}
dot_config/zsh/zprofile.d/10-tty-hyprland.zsh
# dot_config/hyprland/
# dot_config/waybar/
# dot_config/mako/
{{- end }}

# ── Any desktop (exclude from CLI/server) ───────────────────
{{- if eq .desktop "none" }}
# dot_config/zsh/zshrc.d/42-desktop-aliases.zsh
# dot_config/ghostty/
{{- end }}

# ── CLI/server only (exclude from desktop) ──────────────────
{{- if ne .desktop "none" }}
# dot_config/zsh/zshrc.d/42-server-aliases.zsh
{{- end }}

# ════════════════════════════════════════════════════════════
# Profile-gated files
# ════════════════════════════════════════════════════════════

# ── Work profile only ───────────────────────────────────────
# Corporate proxies, internal tool aliases, k8s configs
{{- if ne .profile "work" }}
# dot_config/zsh/zshenv.d/07-work-proxy.zsh
# dot_config/zsh/zshrc.d/25-kubectl.zsh
# dot_config/zsh/zshrc.d/42-work-aliases.zsh
# dot_config/git/config-work
{{- end }}

# ── Personal profile only ──────────────────────────────────
# Gaming, personal project shortcuts
{{- if ne .profile "personal" }}
# dot_config/zsh/zshrc.d/42-gaming-aliases.zsh
{{- end }}

# ════════════════════════════════════════════════════════════
# Host-gated files (use sparingly — prefer profile/desktop)
# ════════════════════════════════════════════════════════════

# ── Gaming PC only ──────────────────────────────────────────
# {{- if ne .hostname "gaming-pc" }}
# dot_config/zsh/zshrc.d/43-gamemode.zsh
# dot_config/mangohud/
# {{- end }}

# ── Specific work server ────────────────────────────────────
# {{- if ne .hostname "prod-1" }}
# dot_config/zsh/zshrc.d/43-prod-monitoring.zsh
# {{- end }}
```

**Gating hierarchy:** prefer `profile` > `desktop` > `os` >
`hostname`. Most files should gate on profile or desktop. Hostname
gating is a last resort for truly unique machines.

### Gating Matrix

| Machine | `.osid` | `.desktop` | `.profile` | Gets |
|---|---|---|---|---|
| Work Arch laptop | `arch` | `hyprland` | `work` | Full desktop + work aliases, kubectl, proxy |
| Home gaming PC | `arch` | `hyprland` | `personal` | Full desktop + gaming aliases |
| Work Ubuntu server | `ubuntu` | `none` | `work` | CLI only + work aliases, server aliases |
| College Mac laptop | `darwin` | `none` | `personal` | Full run (macOS always desktop) + personal aliases |
| Work Arch SSH server | `arch` | `none` | `work` | CLI only + work aliases, server aliases |

### `run_onchange_after_ansible.sh.tmpl`

Runs whenever any Ansible file changes (hash-triggered). Installs
Ansible if missing, then runs the playbook with tags determined by
the `.desktop` value from `chezmoi.toml`.

```bash
#!/usr/bin/env bash
set -euo pipefail

# ── Ansible file hashes (triggers re-run on change) ─────────
# site.yml hash: {{ include "ansible/site.yml" | sha256sum }}
# base/main hash: {{ include "ansible/roles/base/tasks/main.yml" | sha256sum }}
# base/arch hash: {{ include "ansible/roles/base/tasks/arch.yml" | sha256sum }}
# base/ubuntu hash: {{ include "ansible/roles/base/tasks/ubuntu.yml" | sha256sum }}
# zsh hash: {{ include "ansible/roles/zsh/tasks/main.yml" | sha256sum }}
# dev hash: {{ include "ansible/roles/dev/tasks/main.yml" | sha256sum }}
# hyprland hash: {{ include "ansible/roles/hyprland/tasks/main.yml" | sha256sum }}
# ghostty-terminfo hash: {{ include "ansible/files/ghostty.terminfo" | sha256sum }}

# ── Install Ansible if missing ───────────────────────────────
if ! command -v ansible-playbook &>/dev/null; then
{{- if eq .osid "arch" }}
  sudo pacman -S --needed --noconfirm ansible
{{- else if eq .osid "ubuntu" }}
  sudo apt update && sudo apt install -y ansible
{{- else if eq .osid "fedora" }}
  sudo dnf install -y ansible
{{- else if eq .osid "darwin" }}
  brew install ansible
{{- end }}
fi

# ── Run Ansible ──────────────────────────────────────────────
cd {{ .chezmoi.sourceDir }}/ansible

{{- if eq .desktop "none" }}
echo "[chezmoi] Running Ansible (CLI mode — {{ .profile }})"
ansible-playbook site.yml --tags cli --ask-become-pass
{{- else }}
echo "[chezmoi] Running Ansible (desktop: {{ .desktop }} — {{ .profile }})"
ansible-playbook site.yml --ask-become-pass
{{- end }}
```

**How it works:**

- Each hash comment contains a `{{ include ... | sha256sum }}`
  call. When any included file changes, the rendered script
  content changes, and chezmoi treats it as a new script to
  execute.
- On first `chezmoi apply`, all hashes are new so the script runs.
- On subsequent runs, it only re-runs if an Ansible file actually
  changed.
- `.desktop` and `.profile` values come from `chezmoi.toml`,
  persisted during `chezmoi init`.

---

## Ansible Architecture

### Design principles

- **One playbook, all vars inline.** No `group_vars/` directory,
  no `inventory.yml`. Everything visible in `site.yml`.
- **Roles for separation.** `base`, `zsh`, `dev`, `hyprland`.
- **Tags for selectivity.** `--tags cli` for headless/server,
  full run for desktop.
- **Data-driven over conditional sprawl.** Package lists, driver
  maps, XDG dir lists — not nested if/else.
- **Infrastructure before packages.** `arch.yml` builds yay —
  then `main.yml` installs everything.
- **Homebrew is a prerequisite, not managed by Ansible.** On
  macOS, Homebrew must already be installed (it's needed to
  install chezmoi itself).
- **Package lists are centralized** in `site.yml` vars. Distro
  files (`arch.yml`, `ubuntu.yml`) are infrastructure and fixups
  only — never package manifests.

### Execution order

```text
pre_tasks:
  ├── validate OS
  ├── detect Nvidia GPU
  ├── set nvidia_generation fact
  └── append nvidia packages to aur_packages

roles:
  1. base
  │   Phase 1: Create XDG directories
  │   Phase 2: Infrastructure (yay bootstrap — Arch only)
  │   Phase 3: Package installation (pacman / apt / dnf / brew / yay)
  │   Phase 4: Post-install fixups (Ubuntu symlinks)
  │   Phase 5: Ghostty terminfo (Ubuntu — compiled from vendored source)
  │
  2. zsh ──── default shell, omz, p10k
  │
  3. dev ──── rust toolchain, node LTS
  │
  4. hyprland ── compositor + desktop utilities (Arch only)
```

### Tags

| Tag | What runs |
|---|---|
| `ansible-playbook site.yml` | Everything |
| `--tags cli` | base + zsh + dev (no desktop) |
| `--tags base` | Packages and infrastructure only |
| `--tags desktop` | Hyprland role only |
| `--tags zsh` | Shell setup only |
| `--tags dev` | Toolchain setup only |

---

## Ansible Files

### `ansible/site.yml`

```yaml
---
- name: Workstation bootstrap
  hosts: localhost
  connection: local
  become: false

  vars:
    # ── XDG Base Directories ────────────────────────────────
    xdg_config_home: "{{ ansible_env.HOME }}/.config"
    xdg_cache_home: "{{ ansible_env.HOME }}/.cache"
    xdg_data_home: "{{ ansible_env.HOME }}/.local/share"
    xdg_state_home: "{{ ansible_env.HOME }}/.local/state"
    local_bin: "{{ ansible_env.HOME }}/.local/bin"

    xdg_dirs:
      - "{{ xdg_config_home }}"
      - "{{ xdg_cache_home }}"
      - "{{ xdg_data_home }}"
      - "{{ xdg_state_home }}"
      - "{{ local_bin }}"
      - "{{ xdg_state_home }}/zsh"
      - "{{ xdg_cache_home }}/zsh"

    # ── XDG environment for subprocesses ────────────────────
    # Mirrors zshenv.d/06-xdg-apps.zsh so Ansible operations
    # and shell runtime use identical paths. When adding a new
    # redirect in 06-xdg-apps.zsh, add it here too.
    xdg_environment:
      XDG_CONFIG_HOME: "{{ xdg_config_home }}"
      XDG_CACHE_HOME: "{{ xdg_cache_home }}"
      XDG_DATA_HOME: "{{ xdg_data_home }}"
      XDG_STATE_HOME: "{{ xdg_state_home }}"
      CARGO_HOME: "{{ xdg_data_home }}/cargo"
      RUSTUP_HOME: "{{ xdg_data_home }}/rustup"
      GOPATH: "{{ xdg_data_home }}/go"
      GOMODCACHE: "{{ xdg_cache_home }}/go/mod"
      BUN_INSTALL: "{{ xdg_data_home }}/bun"
      DOTNET_CLI_HOME: "{{ xdg_data_home }}/dotnet"
      NPM_CONFIG_CACHE: "{{ xdg_cache_home }}/npm"
      GNUPGHOME: "{{ xdg_data_home }}/gnupg"

    # ── Oh My Zsh ───────────────────────────────────────────
    omz_dir: "{{ xdg_data_home }}/oh-my-zsh"
    p10k_dir: "{{ omz_dir }}/custom/themes/powerlevel10k"

    # ── Packages ────────────────────────────────────────────
    # All package lists in one place for clear visibility.
    # neovim is intentionally absent from common — Arch gets
    # neovim-git via yay, others get it in distro_packages.
    common_packages:
      - git
      - zsh
      - fzf
      - ripgrep
      - eza
      - zoxide
      - tmux
      - curl
      - wget
      - unzip
      - bat
      - bottom
      - rustup
      - fnm

    distro_packages:
      Archlinux:
        - fd
        - openssh
        - man-db
        - ghostty-terminfo
      Ubuntu:
        - neovim
        - fd-find
        - openssh-server
        - man-db
      Fedora:
        - neovim
        - fd-find
        - openssh-server
        - man-db
        - ghostty-terminfo
      Darwin:
        - neovim
        - fd

    # AUR packages — nvidia packages appended dynamically
    aur_packages:
      - neovim-git

    macos_casks:
      - ghostty
      - font-jetbrains-mono-nerd-font

  environment: "{{ xdg_environment }}"

  pre_tasks:
    - name: Fail on unsupported OS
      ansible.builtin.fail:
        msg: >-
          Unsupported: {{ ansible_distribution }}
          ({{ ansible_os_family }}).
          Supported: Archlinux, Ubuntu, Fedora, macOS.
      when: >-
        ansible_distribution not in distro_packages
        and ansible_os_family != 'Darwin'

    # ── Nvidia GPU detection ──────────────────────────────
    #   Blackwell+ (RTX 50xx)          → nvidia-open-beta-dkms
    #   Turing–Ada (RTX 20–40, GTX 16) → nvidia-beta-dkms
    #   Pascal (GTX 10xx)              → nvidia-580xx-dkms
    - name: Detect Nvidia GPU
      ansible.builtin.shell: |
        lspci | grep -iE 'vga|3d' | grep -i nvidia
      register: nvidia_detect
      changed_when: false
      failed_when: false
      when: ansible_system == 'Linux'

    - name: Set Nvidia generation
      ansible.builtin.set_fact:
        nvidia_generation: >-
          {%- set gpu = nvidia_detect.stdout | default('') -%}
          {%- if gpu is search('RTX [5-9]0') -%}blackwell
          {%- elif gpu is search('RTX [2-4]0|GTX 16') -%}turing_ada
          {%- elif gpu is search('GTX 10') -%}pascal
          {%- else -%}none
          {%- endif -%}

    - name: Build Nvidia package list and append to AUR packages
      vars:
        nvidia_driver_map:
          blackwell:
            - linux-headers
            - nvidia-open-beta-dkms
            - nvidia-utils-beta
            - nvidia-settings-beta
            - libva-nvidia-driver
          turing_ada:
            - linux-headers
            - nvidia-beta-dkms
            - nvidia-utils-beta
            - nvidia-settings-beta
            - libva-nvidia-driver
          pascal:
            - linux-headers
            - nvidia-580xx-dkms
            - nvidia-580xx-utils
          none: []
      ansible.builtin.set_fact:
        has_nvidia: "{{ nvidia_generation != 'none' }}"
        nvidia_packages: "{{ nvidia_driver_map[nvidia_generation] }}"
        aur_packages: "{{ aur_packages + nvidia_driver_map[nvidia_generation] }}"

  roles:
    - { role: base, tags: [base, cli] }
    - { role: zsh, tags: [zsh, cli] }
    - { role: dev, tags: [dev, cli] }
    - { role: hyprland, tags: [desktop] }
```

### `roles/base/tasks/main.yml`

```yaml
---
# ════════════════════════════════════════════════════════════
# Phase 1: XDG directories — before anything writes to disk
# ════════════════════════════════════════════════════════════

- name: Create XDG base directories
  ansible.builtin.file:
    path: "{{ item }}"
    state: directory
    mode: "0755"
  loop: "{{ xdg_dirs }}"

# ════════════════════════════════════════════════════════════
# Phase 2: Infrastructure — package managers that need setup
# ════════════════════════════════════════════════════════════
# Note: Homebrew is a prerequisite on macOS (needed to install
# chezmoi itself). Ansible does not bootstrap or manage it.

- name: Include Arch infrastructure (yay)
  ansible.builtin.include_tasks: arch.yml
  when: ansible_distribution == 'Archlinux'

# ════════════════════════════════════════════════════════════
# Phase 3: Package installation — all platforms
# ════════════════════════════════════════════════════════════

- name: Install packages (pacman)
  become: true
  community.general.pacman:
    name: "{{ common_packages + distro_packages['Archlinux'] }}"
    state: present
    update_cache: true
  when: ansible_distribution == 'Archlinux'

- name: Install packages (apt)
  become: true
  ansible.builtin.apt:
    name: "{{ common_packages + distro_packages['Ubuntu'] }}"
    state: present
    update_cache: true
  when: ansible_distribution == 'Ubuntu'

- name: Install packages (dnf)
  become: true
  ansible.builtin.dnf:
    name: "{{ common_packages + distro_packages['Fedora'] }}"
    state: present
  when: ansible_distribution == 'Fedora'

- name: Install CLI tools (Homebrew formulae)
  community.general.homebrew:
    name: "{{ common_packages + distro_packages['Darwin'] }}"
    state: present
  when: ansible_os_family == 'Darwin'

- name: Install desktop apps (Homebrew casks)
  community.general.homebrew_cask:
    name: "{{ macos_casks }}"
    state: present
  when: ansible_os_family == 'Darwin'

- name: Install AUR packages
  ansible.builtin.command: >-
    yay -S --needed --noconfirm {{ item }}
  loop: "{{ aur_packages }}"
  register: yay_install
  changed_when: "'there is nothing to do' not in yay_install.stdout"
  when: >-
    ansible_distribution == 'Archlinux'
    and aur_packages | length > 0

# ════════════════════════════════════════════════════════════
# Phase 4: Post-install fixups
# ════════════════════════════════════════════════════════════

- name: Include Ubuntu post-install fixups
  ansible.builtin.include_tasks: ubuntu.yml
  when: ansible_distribution == 'Ubuntu'

# ════════════════════════════════════════════════════════════
# Phase 5: Ghostty terminfo (distros without a package)
# ════════════════════════════════════════════════════════════
# Arch and Fedora get ghostty-terminfo via package manager
# in Phase 3. macOS gets it via the full ghostty cask.
# Ubuntu doesn't package it, so compile from vendored source.
# Ensures SSH servers accept Ghostty terminal connections.
#
# To refresh: infocmp -x xterm-ghostty > ansible/files/ghostty.terminfo

- name: Check for xterm-ghostty terminfo
  ansible.builtin.command: infocmp xterm-ghostty
  register: ghostty_terminfo_check
  changed_when: false
  failed_when: false
  when: ansible_distribution == 'Ubuntu'

- name: Compile ghostty terminfo
  ansible.builtin.command: tic -x {{ role_path }}/../../files/ghostty.terminfo
  when:
    - ansible_distribution == 'Ubuntu'
    - ghostty_terminfo_check.rc != 0
```

### `roles/base/tasks/arch.yml`

```yaml
---
# ── AUR helper (yay) ────────────────────────────────────────
# Pure infrastructure — no packages installed here.
# Must complete before Phase 3 installs AUR packages.

- name: Check if yay is installed
  ansible.builtin.command: which yay
  register: yay_check
  changed_when: false
  failed_when: false

- name: Install yay from AUR
  when: yay_check.rc != 0
  block:
    - name: Install base-devel
      become: true
      community.general.pacman:
        name: base-devel
        state: present

    - name: Clone and build yay
      ansible.builtin.shell: |
        set -euo pipefail
        git clone https://aur.archlinux.org/yay.git /tmp/yay-build
        cd /tmp/yay-build
        makepkg -si --noconfirm
      args:
        executable: /bin/bash
        creates: /usr/bin/yay

    - name: Clean up build directory
      ansible.builtin.file:
        path: /tmp/yay-build
        state: absent

- name: Configure yay devel database
  ansible.builtin.shell: |
    yay -Y --gendb
    yay -Y --devel --save
  changed_when: false
```

### `roles/base/tasks/ubuntu.yml`

```yaml
---
# ── Binary name fixups ──────────────────────────────────────
# Runs after Phase 3 so the binaries exist to symlink.

- name: Symlink Ubuntu binaries to standard names
  become: true
  ansible.builtin.file:
    src: "{{ item.src }}"
    dest: "{{ item.dest }}"
    state: link
    force: true
  loop:
    - { src: /usr/bin/fdfind, dest: /usr/local/bin/fd }
    - { src: /usr/bin/batcat, dest: /usr/local/bin/bat }
```

### `roles/zsh/tasks/main.yml`

```yaml
---
- name: Set zsh as default shell
  become: true
  ansible.builtin.user:
    name: "{{ ansible_user_id }}"
    shell: >-
      {{ '/usr/bin/zsh'
         if ansible_os_family != 'Darwin'
         else '/bin/zsh' }}

- name: Clone oh-my-zsh
  ansible.builtin.git:
    repo: https://github.com/ohmyzsh/ohmyzsh.git
    dest: "{{ omz_dir }}"
    depth: 1
    version: master

- name: Clone powerlevel10k theme
  ansible.builtin.git:
    repo: https://github.com/romkatv/powerlevel10k.git
    dest: "{{ p10k_dir }}"
    depth: 1
    version: master
```

### `roles/dev/tasks/main.yml`

```yaml
---
# rustup and fnm are installed via package managers in the base
# role. This role handles post-install toolchain/runtime setup.

- name: Install default Rust stable toolchain
  ansible.builtin.command: rustup default stable
  args:
    creates: "{{ xdg_data_home }}/rustup/toolchains/stable-*"

- name: Install latest LTS Node via fnm
  ansible.builtin.shell: |
    eval "$(fnm env)"
    fnm install --lts
  args:
    executable: /bin/zsh
    creates: "{{ xdg_data_home }}/fnm/node-versions"
```

### `roles/hyprland/tasks/main.yml`

```yaml
---
# ============================================================
# Hyprland + Wayland on Arch
#
# Reference: https://wiki.hyprland.org/Nvidia/
# Last verified: 2025-03-09
#
# All Nvidia packages (driver, utils, settings, headers, libva)
# are installed via yay in the base role. The nvidia_driver_map
# in site.yml pre_tasks builds the correct list per GPU
# generation. This role has zero Nvidia awareness.
#
# Nvidia env vars belong in hyprland.conf, NOT zsh dotfiles.
# ============================================================

- name: Skip Hyprland role on non-Arch systems
  ansible.builtin.meta: end_role
  when: ansible_distribution != 'Archlinux'

- name: Install Hyprland desktop packages
  become: true
  community.general.pacman:
    name:
      # Compositor
      - hyprland
      - xdg-desktop-portal-hyprland
      - uwsm
      - hyprpolkitagent

      # Terminal & fonts
      - ghostty
      - ttf-jetbrains-mono-nerd

      # Desktop utilities
      - mako
      - wl-clipboard
      - brightnessctl
      - playerctl
      - grim
      - slurp
    state: present
```

---

## Ghostty Terminfo

SSH connections from a Ghostty terminal set `TERM=xterm-ghostty`.
If the remote host lacks the terminfo entry, the terminal
misbehaves (broken display, missing colors, curses errors).

### How each platform resolves this

| Platform | Method |
|---|---|
| Arch | `ghostty-terminfo` package via pacman (in `distro_packages`) |
| Fedora | `ghostty-terminfo` package via dnf (in `distro_packages`) |
| macOS | Full `ghostty` cask includes terminfo |
| Ubuntu | Compiled from vendored `ansible/files/ghostty.terminfo` in Phase 5 |

### Vendored terminfo source

Ubuntu doesn't package `ghostty-terminfo`. The terminfo definition
is exported from a machine that has Ghostty installed and committed
to the repo at `ansible/files/ghostty.terminfo`.

To refresh after a Ghostty update:

```bash
infocmp -x xterm-ghostty > ~/.local/share/chezmoi/ansible/files/ghostty.terminfo
```

Then `chezmoi apply` on Ubuntu servers picks up the new definition
automatically via the `run_onchange` hash trigger.

---

## Nvidia GPU Detection

Runs in `site.yml` `pre_tasks` on Linux only. Detects GPU via
`lspci`, sets `nvidia_generation` fact, looks up packages from a
driver map, and appends them to `aur_packages` so they are
installed alongside other AUR packages in the base role.

`linux-headers` is first in every package list so DKMS modules
can build during driver installation.

| Generation | Detection regex | AUR packages |
|---|---|---|
| blackwell | `RTX [5-9]0` | linux-headers, nvidia-open-beta-dkms, nvidia-utils-beta, nvidia-settings-beta, libva-nvidia-driver |
| turing_ada | `RTX [2-4]0\|GTX 16` | linux-headers, nvidia-beta-dkms, nvidia-utils-beta, nvidia-settings-beta, libva-nvidia-driver |
| pascal | `GTX 10` | linux-headers, nvidia-580xx-dkms, nvidia-580xx-utils |
| none | no match | (nothing appended) |

On macOS and non-Nvidia Linux, detection runs but produces
`nvidia_generation: none` and `aur_packages` is unchanged.

---

## XDG Environment Propagation

`site.yml` sets `environment: "{{ xdg_environment }}"` at the
play level. Every task in every role inherits XDG variables. No
per-task `environment:` blocks needed.

This mirrors `zshenv.d/06-xdg-apps.zsh` so Ansible installs and
shell runtime use identical paths. **When adding a new XDG redirect
in the zsh file, add it to `xdg_environment` in `site.yml` too.**

---

## Adding a New Desktop Environment

Desktop roles are standalone — no dispatcher file.

```text
roles/
├── hyprland/
│   └── tasks/main.yml
└── kde/                       ← just add a new role
    └── tasks/main.yml
```

Each role guards itself with `meta: end_role` so it's safe to
leave multiple listed. Or comment out the inactive one:

```yaml
  roles:
    - { role: base, tags: [base, cli] }
    - { role: zsh, tags: [zsh, cli] }
    - { role: dev, tags: [dev, cli] }
    # - { role: hyprland, tags: [desktop] }
    - { role: kde, tags: [desktop] }
```

When adding a new desktop environment, add it as a valid value for
the `desktop` prompt in `.chezmoi.toml.tmpl` and update
`.chezmoiignore` gating blocks as needed.

---

## Separation of Concerns

| Concern | Owner | NOT owned by |
|---|---|---|
| Machine identity (OS, desktop, profile) | chezmoi `.chezmoi.toml.tmpl` | Ansible |
| Which files exist on a host | chezmoi `.chezmoiignore` | Ansible |
| Dotfile contents | chezmoi source files | Ansible |
| Package installation | Ansible | chezmoi |
| Infrastructure (yay) | Ansible `base/tasks/arch.yml` | — |
| Homebrew | User prerequisite (pre-chezmoi) | Ansible |
| Nvidia driver selection | Ansible `site.yml` pre_tasks | Hyprland role |
| Nvidia env vars | `hyprland.conf` | zsh dotfiles |
| Shell runtime behavior | zsh drop-in dirs | Ansible |
| Ansible re-run triggers | chezmoi `run_onchange_` hash comments | — |

---

## Full Trace: Fresh Arch Desktop + RTX 4080 (work)

```text
USER RUNS:
  sudo pacman -S --needed git chezmoi
  chezmoi init --apply PixelHabits

CHEZMOI INIT PROMPTS:
  Email address: user@company.com
  Desktop environment (hyprland/none): hyprland
  Machine profile (work/personal): work

GENERATES ~/.config/chezmoi/chezmoi.toml:
  osid = "arch"
  hostname = "work-laptop"
  email = "user@company.com"
  desktop = "hyprland"
  profile = "work"

CHEZMOI DEPLOYS:
  ~/.zshenv
  ~/.config/zsh/.zshenv
  ~/.config/zsh/.zprofile
  ~/.config/zsh/.zshrc
  ~/.config/zsh/zshenv.d/00-logging.zsh
  ~/.config/zsh/zshenv.d/05-privacy.zsh
  ~/.config/zsh/zshenv.d/06-xdg-apps.zsh
  ~/.config/zsh/zshenv.d/10-path.zsh
  ~/.config/zsh/zprofile.d/10-tty-hyprland.zsh
  ~/.config/zsh/zshrc.d/01-p10k-instant.zsh
  ~/.config/zsh/zshrc.d/10-history.zsh
  ~/.config/zsh/zshrc.d/11-keybindings.zsh
  ~/.config/zsh/zshrc.d/12-options.zsh
  ~/.config/zsh/zshrc.d/20-oh-my-zsh.zsh
  ~/.config/zsh/zshrc.d/21-fzf.zsh
  ~/.config/zsh/zshrc.d/22-atuin.zsh.disabled
  ~/.config/zsh/zshrc.d/23-zoxide.zsh
  ~/.config/zsh/zshrc.d/40-aliases.zsh
  ~/.config/zsh/zshrc.d/41-functions.zsh
  ~/.config/zsh/zshrc.d/50-completions.zsh
  ~/.config/zsh/zshrc.d/60-p10k-prompt.zsh
  ~/.config/p10k/p10k.zsh

  SKIPPED by .chezmoiignore:
    11-homebrew.zsh         (not darwin)
    ansible/                (source-only)
    README.md               (source-only)
    *.md docs               (source-only)

CHEZMOI RUNS: run_onchange_after_ansible.sh
  ├─ ansible not found
  │  → sudo pacman -S --needed --noconfirm ansible
  └─ ansible-playbook site.yml --ask-become-pass

ANSIBLE pre_tasks:
  ├─ validate OS → Archlinux ✓
  ├─ detect nvidia → "NVIDIA Corporation ... RTX 4080"
  ├─ nvidia_generation → turing_ada
  └─ aur_packages:
       - neovim-git
       - linux-headers
       - nvidia-beta-dkms
       - nvidia-utils-beta
       - nvidia-settings-beta
       - libva-nvidia-driver

ANSIBLE role: base
  Phase 1 — XDG dirs:
    mkdir ~/.config ~/.cache ~/.local/share ~/.local/state
          ~/.local/bin ~/.local/state/zsh ~/.cache/zsh

  Phase 2 — infrastructure (arch.yml):
    ├─ check yay → not found
    ├─ install base-devel via pacman
    ├─ git clone + makepkg yay
    ├─ cleanup /tmp/yay-build
    └─ yay -Y --gendb && yay -Y --devel --save

  Phase 3 — packages:
    ├─ pacman: git zsh fzf ripgrep eza zoxide tmux curl wget
    │         unzip bat bottom rustup fnm fd openssh man-db
    │         ghostty-terminfo
    └─ yay: neovim-git linux-headers nvidia-beta-dkms
            nvidia-utils-beta nvidia-settings-beta
            libva-nvidia-driver

  Phase 4 — (no Ubuntu fixups)
  Phase 5 — (not Ubuntu, skip)

ANSIBLE role: zsh
  ├─ chsh → /usr/bin/zsh
  ├─ git clone oh-my-zsh → ~/.local/share/oh-my-zsh
  └─ git clone p10k → .../custom/themes/powerlevel10k

ANSIBLE role: dev
  ├─ rustup default stable
  └─ fnm install --lts

ANSIBLE role: hyprland
  └─ pacman: hyprland xdg-desktop-portal-hyprland uwsm
             hyprpolkitagent ghostty ttf-jetbrains-mono-nerd
             mako wl-clipboard brightnessctl playerctl grim slurp

DONE. Reboot → tty1 → uwsm start hyprland-uwsm.desktop
```

## Full Trace: Fresh Arch Desktop + No Nvidia (personal)

```text
CHEZMOI INIT PROMPTS:
  Email address: user@personal.com
  Desktop environment (hyprland/none): hyprland
  Machine profile (work/personal): personal

GENERATES chezmoi.toml:
  osid = "arch"
  hostname = "gaming-pc"
  desktop = "hyprland"
  profile = "personal"

ANSIBLE pre_tasks:
  ├─ detect nvidia → not found (rc=1)
  ├─ nvidia_generation → none
  └─ aur_packages: [neovim-git]   ← unchanged

ANSIBLE role: base Phase 3:
  ├─ pacman: (same common + distro incl. ghostty-terminfo)
  └─ yay: neovim-git

ANSIBLE role: hyprland:
  └─ pacman: hyprland uwsm ghostty fonts utilities
     (no nvidia packages anywhere)
```

## Full Trace: Fresh macOS (personal)

```text
USER RUNS:
  brew install chezmoi
  chezmoi init --apply PixelHabits

CHEZMOI INIT PROMPTS:
  Email address: user@college.edu
  Desktop environment (hyprland/none): none
  Machine profile (work/personal): personal

GENERATES chezmoi.toml:
  osid = "darwin"
  hostname = "macbook"
  desktop = "none"
  profile = "personal"

CHEZMOI DEPLOYS:
  (all zsh files)
  11-homebrew.zsh                  ← darwin: included
  SKIPPED: 10-tty-hyprland.zsh    (desktop != hyprland)

CHEZMOI RUNS: run_onchange_after_ansible.sh
  ├─ brew install ansible
  └─ ansible-playbook site.yml --ask-become-pass

ANSIBLE pre_tasks:
  ├─ validate OS → Darwin ✓
  ├─ nvidia detection → skipped (not Linux)
  └─ nvidia_generation: none, aur_packages unchanged

ANSIBLE role: base
  Phase 1 — XDG dirs
  Phase 2 — (Homebrew already installed, no infrastructure)
  Phase 3:
    ├─ brew formulae: git zsh fzf ripgrep eza zoxide tmux curl
    │                 wget unzip bat bottom rustup fnm neovim fd
    └─ brew casks: ghostty font-jetbrains-mono-nerd-font
  Phase 4 — (not Ubuntu)
  Phase 5 — (not Ubuntu)

ANSIBLE role: zsh
  ├─ chsh → /bin/zsh
  ├─ clone oh-my-zsh
  └─ clone p10k

ANSIBLE role: dev → rustup stable, fnm lts
ANSIBLE role: hyprland → meta: end_role (not Arch)

DONE.
```

## Full Trace: Fresh Ubuntu Server (work)

```text
USER RUNS:
  sudo apt install git chezmoi
  chezmoi init --apply PixelHabits

CHEZMOI INIT PROMPTS:
  Email address: user@company.com
  Desktop environment (hyprland/none): none
  Machine profile (work/personal): work

GENERATES chezmoi.toml:
  osid = "ubuntu"
  hostname = "prod-1"
  desktop = "none"
  profile = "work"

CHEZMOI:
  SKIPPED: 11-homebrew.zsh (not darwin)
  SKIPPED: 10-tty-hyprland.zsh (desktop != hyprland)

CHEZMOI RUNS: run_onchange_after_ansible.sh
  ├─ sudo apt update && sudo apt install -y ansible
  └─ ansible-playbook site.yml --tags cli --ask-become-pass

ANSIBLE role: base
  Phase 1 — XDG dirs
  Phase 2 — (apt exists, no infrastructure)
  Phase 3 — apt: git zsh fzf ripgrep eza zoxide tmux curl wget
                  unzip bat bottom rustup fnm neovim fd-find
                  openssh-server man-db
  Phase 4 — ubuntu.yml: symlink fdfind→fd, batcat→bat
  Phase 5 — ghostty terminfo:
    ├─ infocmp xterm-ghostty → not found (rc=1)
    └─ tic -x ansible/files/ghostty.terminfo

ANSIBLE role: zsh → chsh, clone omz + p10k
ANSIBLE role: dev → rustup stable, fnm lts
ANSIBLE role: hyprland → SKIPPED (--tags cli)

DONE.
```

## Full Trace: Fresh Arch SSH Server (work)

```text
CHEZMOI INIT PROMPTS:
  Email address: user@company.com
  Desktop environment (hyprland/none): none
  Machine profile (work/personal): work

GENERATES chezmoi.toml:
  osid = "arch"
  hostname = "build-server"
  desktop = "none"
  profile = "work"

CHEZMOI:
  SKIPPED: 11-homebrew.zsh (not darwin)
  SKIPPED: 10-tty-hyprland.zsh (desktop != hyprland)

CHEZMOI RUNS: run_onchange_after_ansible.sh
  └─ ansible-playbook site.yml --tags cli --ask-become-pass

ANSIBLE role: base
  Phase 2 — arch.yml (yay bootstrap)
  Phase 3:
    ├─ pacman: common + distro incl. ghostty-terminfo
    └─ yay: neovim-git (no nvidia — detection returns none)
  Phase 5 — (not Ubuntu, skip)

ANSIBLE role: zsh → chsh, clone omz + p10k
ANSIBLE role: dev → rustup stable, fnm lts
ANSIBLE role: hyprland → SKIPPED (--tags cli)

DONE.
```

## Subsequent Run: Add a Package

```text
USER EDITS ansible/site.yml:
  Adds "jq" to common_packages

USER RUNS: chezmoi apply

CHEZMOI:
  ├─ Detects site.yml hash changed in run_onchange script
  └─ Re-runs run_onchange_after_ansible.sh

ANSIBLE:
  └─ Installs jq, all other tasks report "ok" (idempotent)
```

---

## Common Workstation Tasks

| Task | How |
|---|---|
| Add a CLI tool | Add to `common_packages` or `distro_packages` in `site.yml`. If it needs shell init, also add `zshrc.d/2x-tool.zsh`. Run `chezmoi apply`. |
| Add an AUR-only package | Add to `aur_packages` in `site.yml`. Run `chezmoi apply`. |
| Add a macOS cask | Add to `macos_casks` in `site.yml`. Run `chezmoi apply`. |
| Add a new XDG redirect | Add export to `zshenv.d/06-xdg-apps.zsh` AND to `xdg_environment` in `site.yml`. |
| Add a new desktop environment | Create `roles/newde/tasks/main.yml` with `meta: end_role` guard. Add to `site.yml` roles. Add as valid `desktop` value. Update `.chezmoiignore`. |
| Support a new distro | Add to `distro_packages`. Add package manager task to `base/tasks/main.yml`. Create fixup file if needed. Update `run_onchange_after_ansible.sh.tmpl`. |
| Re-run Ansible manually | `cd ~/.local/share/chezmoi/ansible && ansible-playbook site.yml --ask-become-pass` |
| Re-run CLI packages only | `ansible-playbook site.yml --tags cli --ask-become-pass` |
| Re-run desktop only | `ansible-playbook site.yml --tags desktop --ask-become-pass` |
| Change machine type | `chezmoi init --prompt` then `chezmoi apply` |
| Refresh ghostty terminfo | `infocmp -x xterm-ghostty > ~/.local/share/chezmoi/ansible/files/ghostty.terminfo` then `chezmoi apply` on target servers |
| Add a host-specific file | Create file in chezmoi source, add gating block in `.chezmoiignore` using `.desktop`, `.profile`, `.chezmoi.os`, or `.hostname` |

---

## Constraints and Invariants

1. `ansible/` is in `.chezmoiignore` — used by run scripts, never
   deployed to `$HOME`.
2. No inventory file. `connection: local` on the play.
3. All Nvidia packages live in `nvidia_driver_map`. The hyprland
   role has zero Nvidia awareness.
4. macOS is always a desktop — casks install in base Phase 3,
   not a separate desktop role. Homebrew is a user prerequisite,
   not managed by Ansible.
5. Ubuntu/Fedora `common_packages` need validation when activated.
   `bottom`, `eza`, `rustup`, `fnm` may require PPAs or alternative
   installation.
6. `xdg_environment` in `site.yml` must stay in sync with
   `zshenv.d/06-xdg-apps.zsh`.
7. Machine identity lives in `chezmoi.toml` (generated from
   `.chezmoi.toml.tmpl`). Ansible run mode is derived from
   `.desktop`, not from interactive prompts at run time.
8. Ghostty terminfo is vendored at `ansible/files/ghostty.terminfo`.
   Arch and Fedora get it via package manager. Ubuntu compiles
   from the vendored source. macOS gets it via the full ghostty
   cask.
9. The `run_onchange_` script re-runs Ansible only when Ansible
   files change. Dotfile-only edits do not trigger Ansible.
