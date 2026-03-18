if require_cmd fd && require_cmd fzf-tmux && require_cmd nvim; then
  alias v='fd --type f --hidden --exclude .git | fzf-tmux -p | xargs -r nvim'
fi

if require_cmd eza; then
  alias ls='eza -lha --icons --no-user --git --no-permissions --sort=name'
fi

# Tmux: attach to existing session or create 'main'
if require_cmd tmux; then
  alias t='tmux attach || tmux new -s main'
fi
