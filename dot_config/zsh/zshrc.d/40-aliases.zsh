# Fuzzy file picker — open selected file in Neovim
if require_cmd fd && require_cmd fzf && require_cmd nvim && require_cmd bat; then
  alias f="fd --type f --hidden --exclude .git --no-ignore | fzf --tmux --multi --select-1 --exit-0 --scheme=path --prompt=' file to edit > ' --preview 'bat --color=always --style=numbers {}' | xargs -r nvim -p"
fi

if require_cmd eza; then
  alias ls='eza -lha --icons --no-user --git --no-permissions --sort=name'
fi

# Tmux: attach to existing session or create 'main'
if require_cmd tmux; then
  alias t='tmux attach || tmux new -s main'
fi
