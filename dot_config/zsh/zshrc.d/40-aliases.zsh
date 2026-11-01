# Fuzzy file picker — open selected file in Neovim
if require_cmd fd && require_cmd fzf && require_cmd nvim && require_cmd bat; then
  alias f="fzf --tmux --multi --select-1 --exit-0 --scheme=path --print0 \
    --prompt=' file to edit > ' --preview '$fzf_file_preview {}' \
    --header='ctrl-y: copy path, alt-y: copy file' \
    --bind 'ctrl-y:execute-silent(realpath -- {+} | wl-copy -n)+abort' \
    --bind 'alt-y:execute-silent(wl-copy < {})+abort' \
    | xargs -0 -r nvim -p"
fi

if require_cmd eza; then
  alias ls='eza -lha --git --hyperlink --icons --no-permissions --no-user --sort=name'
fi

# Tmux: attach to existing session or create 'main'
if require_cmd tmux; then
  alias t='tmux attach || tmux new -s main'
fi
