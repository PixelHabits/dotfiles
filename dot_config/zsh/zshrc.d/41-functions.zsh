# Ripgrep + FZF content search — live grep inside files, open at matching line
if require_cmd rg && require_cmd fzf && require_cmd bat; then
  fr() {
    local result file line
    result=$(fzf --tmux 80%,70% --ansi \
      --disabled \
      --bind 'start:reload:rg --column --line-number --no-heading --color=always --smart-case --no-ignore "" || true' \
      --bind 'change:reload:rg --column --line-number --no-heading --color=always --smart-case --no-ignore {q} || true' \
      --delimiter : \
      --prompt 'ripgrep in files > ' \
      --header 'enter: open in editor' \
      --preview 'bat --color=always --highlight-line {2} -- {1}' \
      --preview-window 'right:60%:+{2}-10')
    file=$(echo "$result" | cut -d: -f1)
    line=$(echo "$result" | cut -d: -f2)
    [[ -n "$file" ]] && ${EDITOR:-nvim} "+$line" "$file"
  }
fi

# Git branch switcher — sorted by most recent commit, preview shows log
if require_cmd git && require_cmd fzf; then
  fgb() {
    local branch
    branch=$(git for-each-ref --sort=-committerdate --format='%(refname:short)' \
        --exclude='refs/remotes/*/HEAD' refs/heads refs/remotes |
      fzf --tmux --prompt='branch > ' \
        --header 'enter: checkout' \
        --preview 'git log --oneline --graph --color=always -20 {}') &&
    git checkout "${branch#origin/}"
  }
fi

# Git log browser — browse commits with diff preview
if require_cmd git && require_cmd fzf; then
  fgl() {
    git log --oneline --graph --color=always --all |
      fzf --height=100% --ansi --no-sort \
        --prompt='commit > ' \
        --header 'enter: view diff in popup, esc: quit' \
        --preview 'git show --color=always --stat $(echo {} | grep -oE "[a-f0-9]{7,}" | head -1)' \
        --bind 'enter:execute(git show --color=always $(echo {} | grep -oE "[a-f0-9]{7,}" | head -1) | less -R)'
  }
fi

# Fuzzy process killer — multi-select with Tab, pass signal as arg (e.g. fkill -9)
if require_cmd fzf; then
  fkill() {
    local pid
    pid=$(ps -ef |
      fzf --tmux --multi --header-lines=1 --accept-nth=2 \
        --prompt='kill > ' \
        --header 'tab: multi-select, enter: kill')
    [[ -n "$pid" ]] && echo "$pid" | xargs kill "${1:--15}"
  }
fi

# 1Password quick-copy — fuzzy search vault items, copy password to clipboard
if require_cmd op && require_cmd jq && require_cmd fzf; then
  fp() {
    setopt local_options pipefail
    local item
    item=$(op item list --format=json | jq -r '.[] | [.id, .title] | @tsv' |
      fzf --tmux --delimiter='\t' --with-nth=2 --prompt='1password > ' \
        --header 'enter: copy password') &&
    op item get "${item%%$'\t'*}" --fields label=password --reveal | wl-copy -n --sensitive &&
    echo "Copied password for: ${item#*$'\t'}"
  }
fi
