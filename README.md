# Dotfiles

Chezmoi manages user configuration across machines.
Ansible installs packages and configures system services.

## Start here

Follow [Git worktrees and chezmoi](worktrees.md) to create a new machine setup.
The repository uses `.bare` for Git history and separate directories for each branch.
Use `main` for stable changes and `dev` for ongoing development.

Chezmoi asks for these machine choices:

- Email address for Git
- Desktop environment
- Laptop, desktop, or server
- Work or personal profile
- Development tools

Chezmoi can run Ansible after it deploys files.
On Arch, Ansible asks to add CachyOS repositories when those repositories are absent.

## Common tasks

| Task | Command |
| --- | --- |
| Show the selected source | `chezmoi execute-template '{{ .chezmoi.sourceDir }}'` |
| Review the selected source | `chezmoi diff` |
| Edit the selected source | `chezmoi edit ~/.config/zsh/zshrc.d/40-aliases.zsh` |
| Deploy the selected source | `chezmoi apply` |
| Review a feature | `chezmoi --source ~/.local/share/chezmoi/pwa-web-apps diff` |
| Debug shell startup | `ZSH_BOOT_DEBUG=1 zsh` |

## Documentation

| Document | Purpose |
| --- | --- |
| [Web app workspaces](pwa.md) | App shortcuts and per-machine providers |
| [Worktrees](worktrees.md) | Setup, source selection, and pull requests |
| [Agent instructions](AGENTS.md) | Coding rules and worktree boundaries |
| [Workstation bootstrap](workstation-bootstrap.md) | Chezmoi and Ansible responsibilities |
| [Shell architecture](zsh-dotfile-architecture.md) | Shell configuration structure |
| [Suspend recovery](suspend-recovery.md) | Display recovery and hardware test limits |
| [Hyprland](hyprland.md) | Native Lua configuration and first deployment |
