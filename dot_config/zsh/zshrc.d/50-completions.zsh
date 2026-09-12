# zshrc.d/50-completions.zsh — completion system

[[ -d "$XDG_CACHE_HOME/zsh" ]] || mkdir -p "$XDG_CACHE_HOME/zsh"

autoload -Uz compinit
compinit -d "$XDG_CACHE_HOME/zsh/zcompdump-${ZSH_VERSION}"

# The Bun completion script calls compdef, so load it after compinit.
if [[ -n "${BUN_INSTALL:-}" && -r "$BUN_INSTALL/_bun" ]]; then
  source "$BUN_INSTALL/_bun"
fi

zlog "completions loaded"
