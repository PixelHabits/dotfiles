# zshrc.d/23-zoxide.zsh

require_cmd zoxide || return 0
zlog "init zoxide"

eval "$(zoxide init zsh)"
