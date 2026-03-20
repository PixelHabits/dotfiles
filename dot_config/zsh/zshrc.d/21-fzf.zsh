# zshrc.d/21-fzf.zsh — fzf shell integration
require_cmd fzf || return 0
zlog "init fzf"

# ── Theme (Tomorrow Night via Ghostty + GitHub muted accents) ─
# bg:-1 = transparent (terminal default), ANSI refs for palette colors.
export FZF_DEFAULT_OPTS=" \
  --color=bg:-1,bg+:#1c2128,fg:-1,fg+:15 \
  --color=hl:10,hl+:10,info:4,prompt:4 \
  --color=pointer:4,marker:10,spinner:4,header:#9097a0 \
  --color=border:#9097a0 \
  --reverse --border --height=60% \
  --highlight-line --cycle --info=inline-right \
  --bind 'ctrl-/:toggle-preview' \
  --bind 'alt-up:preview-up,alt-down:preview-down'"

# Use fd if available
if require_cmd fd; then
  export FZF_DEFAULT_COMMAND='fd --type f --hidden --exclude .git'
  export FZF_CTRL_T_COMMAND="$FZF_DEFAULT_COMMAND"
  export FZF_ALT_C_COMMAND='fd --type d --hidden --exclude .git'
fi

# Ctrl+T file picker
export FZF_CTRL_T_OPTS="--tmux --scheme=path --filepath-word --select-1 --exit-0 \
  --prompt='file path > ' --preview 'bat --color=always --style=numbers {}'"

# Alt+C directory changer (replaces fcd)
export FZF_ALT_C_OPTS="--tmux --scheme=path \
  --prompt='change directory > ' --preview 'eza --color=always -lha --icons --no-user --git --no-permissions --sort=name {}'"

# Ctrl+R history
export FZF_CTRL_R_OPTS="--tmux --scheme=history --no-sort \
  --prompt='history > ' \
  --bind 'ctrl-y:execute-silent(echo -n {2..} | wl-copy)+abort' \
  --header='ctrl-y: copy to clipboard'"

# Activate keybindings and completion
source <(fzf --zsh)
