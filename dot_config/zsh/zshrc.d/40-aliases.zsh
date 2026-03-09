if require_cmd fd && require_cmd fzf-tmux && require_cmd nvim; then
  alias v='fd --type f --hidden --exclude .git | fzf-tmux -p | xargs -r nvim'
fi

if require_cmd eza; then
  alias ls='eza -lha --icons --no-user --git --no-permissions --sort=name'
fi
