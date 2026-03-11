# dotfiles

A modular, XDG-compliant, multi-OS dotfile and machine provisioning system managed by Chezmoi and Ansible.

## Documentation

- [Workstation Bootstrap Architecture](workstation-bootstrap.md): Chezmoi gating, Ansible playbook structure, Nvidia detection, and machine identity.
- [ZSH Dotfiles Architecture](zsh-dotfile-architecture.md): ZSH boot chain, deterministic drop-in loading, and XDG environment routing.

## Installation

Install Chezmoi using your system's package manager, then initialize and apply the repository. The commands below combine both steps for a seamless initial setup.

### Arch Linux

```bash
sudo pacman -S --needed git chezmoi && chezmoi init --apply PixelHabits
```

### macOS

_Requires Homebrew._

```bash
brew install chezmoi && chezmoi init --apply PixelHabits
```

### Ubuntu / Debian

```bash
sudo apt update && sudo apt install -y git chezmoi && chezmoi init --apply PixelHabits
```

### Fedora

```bash
sudo dnf install -y git chezmoi && chezmoi init --apply PixelHabits
```

### Using a Private Repository

If this repository is private, ensure your SSH keys are present on the machine and use the SSH URL instead:

```bash
chezmoi init --apply git@github.com:PixelHabits/dotfiles.git
```

## Bootstrapping Process

When you run the `init --apply` command, the following sequence occurs:

1. **Identity:** Chezmoi prompts for your email, desktop environment (`hyprland` or `none`), and profile (`work` or `personal`).
2. **Deploy:** Dotfiles are deployed to their specific XDG-compliant locations. Host-specific files are gated based on your identity answers.
3. **Provision:** A background script automatically installs Ansible (if missing) and executes the playbook. You will be prompted for your `sudo` password to install system packages.

## Common Operations

**Edit a configuration file:**

```bash
chezmoi edit ~/.config/zsh/zshrc.d/40-aliases.zsh
chezmoi apply
```

**Add a new package to Ansible:**

```bash
chezmoi cd
# Edit ansible/site.yml
exit
chezmoi apply
```

_Note: Chezmoi detects changes to Ansible file hashes and automatically triggers a playbook run._

**Change machine identity (e.g., switch from CLI to Desktop):**

```bash
chezmoi init --prompt
chezmoi apply
```
