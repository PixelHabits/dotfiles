# dotfiles

This repo contains the configuration to setup my machines. This is using [Chezmoi](https://chezmoi.io), the dotfile manager to setup the install.


## How to Install and Initialize Chezmoi (shay-mwa)

You can install ChezMoi using the appropriate package manager for your system, or you can use the curl method. Follow the instructions below to set up your dotfiles.

### Using a Package Manager

#### On macOS

**First, ensure Homebrew is installed:**
```shell
if ! command -v brew &> /dev/null; then
    echo "Homebrew not found, installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    else 
    echo "Homebrew already installed."
fi
```

**Then, install & initialize Chezmoi:**

```shell
brew install chezmoi
export GITHUB_USERNAME=pixelhabits # Replace with your GitHub username
chezmoi init --apply https://github.com/$GITHUB_USERNAME/dotfiles.git
```
**For Private Repos**
```shell
brew install chezmoi
export GITHUB_USERNAME=pixelhabits # Replace with your GitHub username
chezmoi init --apply git@github.com:$GITHUB_USERNAME/dotfiles.git
```
#### On Arch
**I use Arch, btw... 😎**
```shell
sudo pacman -Sy chezmoi
export GITHUB_USERNAME=pixelhabits # Replace with your GitHub username
chezmoi init --apply $GITHUB_USERNAME
```
**For Private Repos**
```shell
sudo pacman -Sy chezmoi
export GITHUB_USERNAME=pixelhabits # Replace with your GitHub username
chezmoi init --apply git@github.com:$GITHUB_USERNAME/dotfiles.git
```

#### On Ubuntu
```shell
sudo apt-get update
sudo apt-get install -y chezmoi
export GITHUB_USERNAME=pixelhabits # Replace with your GitHub username
chezmoi init --apply $GITHUB_USERNAME
```
**For Private Repos**
```shell
sudo apt-get update
sudo apt-get install -y chezmoi
export GITHUB_USERNAME=pixelhabits # Replace with your GitHub username
chezmoi init --apply git@github.com:$GITHUB_USERNAME/dotfiles.git
```
