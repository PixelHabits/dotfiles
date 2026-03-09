# zshrc.d/50-completions.zsh — completion system

[[ -d "$XDG_CACHE_HOME/zsh" ]] || mkdir -p "$XDG_CACHE_HOME/zsh"

[[ -s "$HOME/.bun/_bun" ]] && source "$HOME/.bun/_bun"

autoload -Uz compinit
compinit -d "$XDG_CACHE_HOME/zsh/zcompdump-${ZSH_VERSION}"

zlog "completions loaded"
