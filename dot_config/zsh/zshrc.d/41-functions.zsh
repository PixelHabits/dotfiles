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

# Git log browser — current branch with diff preview; arguments go to git log (fgl --all, fgl -- path)
if require_cmd git && require_cmd fzf; then
  fgl() {
    # Field 2 holds the full commit ID, hidden from view. Rows that only draw graph lines leave it empty.
    git log --graph --color=always --format='%x09%H%x09%C(auto)%h %s%d' "$@" |
      fzf --height=100% --ansi --no-sort --delimiter='\t' --with-nth=1,3.. \
        --prompt='commit > ' \
        --header 'enter: view diff, esc: quit' \
        --preview '[ -n {2} ] && git show --color=always --stat {2}' \
        --bind 'enter:execute([ -n {2} ] && git show --color=always {2} | less -R)'
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
