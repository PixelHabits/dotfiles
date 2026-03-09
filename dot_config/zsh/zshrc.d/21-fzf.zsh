# zshrc.d/21-fzf.zsh — fzf shell integration
require_cmd fzf || return 0
zlog "init fzf"

source <(fzf --zsh)
