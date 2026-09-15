# zshrc.d/50-completions.zsh — completion system

[[ -d "$XDG_CACHE_HOME/zsh" ]] || mkdir -p "$XDG_CACHE_HOME/zsh"

autoload -Uz compinit
compinit -d "$XDG_CACHE_HOME/zsh/zcompdump-${ZSH_VERSION}"

# _bun calls compdef, so load it after compinit.
[[ -r "$BUN_INSTALL/_bun" ]] && source "$BUN_INSTALL/_bun"

zlog "completions loaded"
