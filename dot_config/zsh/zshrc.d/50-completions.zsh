# zshrc.d/50-completions.zsh — completion system

[[ -d "$XDG_CACHE_HOME/zsh" ]] || mkdir -p "$XDG_CACHE_HOME/zsh"

autoload -Uz compinit
compinit -d "$XDG_CACHE_HOME/zsh/zcompdump-${ZSH_VERSION}"

zlog "completions loaded"
