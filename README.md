# dotfiles

Cross-platform dotfiles and machine provisioning via Chezmoi + Ansible.

## Quick Start

```bash
# Arch
sudo pacman -S --needed git chezmoi
chezmoi init --apply PixelHabits

# macOS (requires Homebrew)
brew install chezmoi
chezmoi init --apply PixelHabits

# Ubuntu
sudo apt update
sudo apt install -y git chezmoi
chezmoi init --apply PixelHabits

# Fedora
sudo dnf install -y git chezmoi
chezmoi init --apply PixelHabits
```

You'll be prompted for:
- **Email** — for git config
- **Desktop** — `hyprland` or `none`
- **Profile** — `work` or `personal`

Ansible runs automatically after dotfiles deploy.

## Common Operations

```bash
# Edit and apply a config
chezmoi edit ~/.config/zsh/zshrc.d/40-aliases.zsh
chezmoi apply

# Add a package (edit ansible/site.yml, then apply)
chezmoi cd
nvim ansible/site.yml
chezmoi apply

# Change machine identity
chezmoi init --prompt
chezmoi apply

# Debug zsh startup
ZSH_BOOT_DEBUG=1 zsh
```

## Documentation

| Doc | Purpose |
|-----|---------|
| [AGENTS.md](AGENTS.md) | Coding standards and conventions |
| [workstation-bootstrap.md](workstation-bootstrap.md) | Chezmoi/Ansible architecture |
| [zsh-dotfile-architecture.md](zsh-dotfile-architecture.md) | Shell configuration structure |
