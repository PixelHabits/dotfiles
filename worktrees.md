# Git worktrees and chezmoi

A worktree is a separate checkout of a Git branch.
A bare repository stores the shared Git history without checked-out files.

## Directory layout

```text
~/.local/share/chezmoi/
├── .bare/
├── main/
├── dev/
└── pwa-web-apps/
```

| Directory | Purpose |
| --- | --- |
| `.bare` | Shared Git history and branch records |
| `main` | Stable branch |
| `dev` | Development branch |
| Feature directories | Changes for individual pull requests |

Use `dev` for ongoing development and feature branches for focused changes.
Commit work on either branch as needed.
Keep unrelated changes separate when you prepare a pull request.

## Set up a new machine

Install Git and chezmoi first.
On macOS, install Homebrew first.

| Platform | Install command |
| --- | --- |
| Arch | `sudo pacman -S --needed git chezmoi` |
| macOS | `brew install git chezmoi` |
| Ubuntu | `sudo apt update && sudo apt install -y git chezmoi` |
| Fedora | `sudo dnf install -y git chezmoi` |

If the directory already contains a checkout, preserve it before you start.
These commands create a new layout:

```sh
mkdir -p ~/.local/share/chezmoi
cd ~/.local/share/chezmoi
git clone --bare https://github.com/PixelHabits/dotfiles.git .bare
git --git-dir=.bare config remote.origin.fetch '+refs/heads/*:refs/remotes/origin/*'
git --git-dir=.bare fetch origin
git --git-dir=.bare worktree add main main
git -C main branch --set-upstream-to=origin/main main
chezmoi --source "$PWD/main" init
chezmoi diff
chezmoi apply
```

The fetch rule keeps remote branches under `origin/`.
Chezmoi asks for machine choices during initialization.
The final command deploys files and can run Ansible.
Do not clone with `chezmoi init <repo>` into the directory that contains all worktrees.

## Select the live source

Chezmoi uses the top-level `sourceDir` value in `~/.config/chezmoi/chezmoi.toml`.
Keep the value before any `[table]` section.
Use an absolute path for your machine:

```toml
sourceDir = "/home/devinalsup/.local/share/chezmoi/main"
```

To use the development branch, change the final directory to `dev`.
Changing this value does not deploy files.
Changing the shell directory does not change this value.
The current template preserves the selected worktree when you run `chezmoi init`.

Display the selected source:

```sh
chezmoi execute-template '{{ .chezmoi.sourceDir }}'
```

## Review a feature

Create a branch from the latest remote main:

```sh
git -C ~/.local/share/chezmoi/main fetch origin
git --git-dir="$HOME/.local/share/chezmoi/.bare" worktree add -b pwa-web-apps "$HOME/.local/share/chezmoi/pwa-web-apps" origin/main
chezmoi --source ~/.local/share/chezmoi/pwa-web-apps diff
```

Use `--source` on feature commands to select that worktree for one command.
Each worktree uses the same local machine data unless you pass a separate `--config` file.
All worktrees share your home directory as the deployment target.

The Ansible script contains the source path.
A change of worktree can cause that script to run again.
For a dotfile-only trial, name the files and exclude scripts:

```sh
chezmoi --source ~/.local/share/chezmoi/pwa-web-apps --exclude scripts apply ~/.config/hypr/hyprland.conf
```

Review the diff for those files before you apply them.
Include each new helper or included configuration file that the feature needs.

## Land a feature

Commit the feature and open a pull request against `main`.
After the pull request merges, update the main checkout:

```sh
git -C ~/.local/share/chezmoi/main pull --ff-only
chezmoi --source ~/.local/share/chezmoi/main diff
```

Review the changes before you deploy them.
Choose `main` or `dev` as your live source to match your workflow.
Updating a branch does not change the selected source.
Make sure that a worktree is ready before you update its branch.
