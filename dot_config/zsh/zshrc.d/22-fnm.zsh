# zshrc.d/22-fnm.zsh — fnm (node version manager) shell integration
require_cmd fnm || return 0
zlog "init fnm"

eval "$(fnm env --use-on-cd)"
