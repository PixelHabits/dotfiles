# dotfiles

This repo contains the configuration to setup my machines. This is using [Chezmoi](https://chezmoi.io), the dotfile manager to setup the install.

<!-- This automated setup is currently only configured for Fedora machines. -->

## How to run

```shell
export GITHUB_USERNAME=pixelhabits
sh -c "$(curl -fsLS get.chezmoi.io)" -- init --apply $GITHUB_USERNAME
```
or For Private Repos

```shell
export GITHUB_USERNAME=pixelhabits
sh -c "$(curl -fsLS get.chezmoi.io)" -- init --apply git@github.com:$GITHUB_USERNAME/dotfiles.git
```


