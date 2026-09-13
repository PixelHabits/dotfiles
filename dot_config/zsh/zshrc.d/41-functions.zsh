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
    branch=$(git branch --all --sort=-committerdate --format='%(refname:short)' |
      fzf --tmux --prompt='branch > ' \
        --header 'enter: checkout' \
        --preview 'git log --oneline --graph --color=always -20 {}') &&
    git checkout "$branch"
  }
fi

# Git log browser — browse commits with diff preview
if require_cmd git && require_cmd fzf; then
  fgl() {
    local -a log_args path_args
    local arg after_separator=false
    for arg in "$@"; do
      if [[ $after_separator == true ]]; then
        path_args+=("$arg")
      elif [[ $arg == -- ]]; then
        after_separator=true
        path_args+=(--)
      elif [[ $arg == -a ]]; then
        log_args+=(--all)
      else
        log_args+=("$arg")
      fi
    done

    # The graph is field 1, the full commit ID is field 2, and the label is field 3.
    # Connector-only rows stay visible but cannot preview or open a commit.
    local valid_hash='printf %s {2} | grep -Eq "^[0-9a-f]{40}([0-9a-f]{24})?$"'

    setopt localoptions pipefail
    if git log "${log_args[@]}" --graph --color=always --no-patch \
      --format='%x09%H%x09%C(auto)%h %s%d' "${path_args[@]}" |
      fzf --height=100% --ansi --no-sort --delimiter=$'\t' --with-nth=1,3.. \
        --prompt='commit > ' \
        --header 'enter: view diff in popup, esc: quit, --all: include all refs' \
        --preview "$valid_hash && git show --color=always --stat {2} --" \
        --bind "enter:execute($valid_hash && git show --color=always {2} -- | less -R)"; then
      return 0
    else
      local -a results=("${pipestatus[@]}")
      # Cancellation can interrupt Git or close its pipe. Other failures remain errors.
      (( results[1] != 0 && results[1] != 141 && results[1] != 130 )) && return "$results[1]"
      (( results[2] == 1 || results[2] == 130 )) && return 0
      return "$results[2]"
    fi
  }
fi

# Fuzzy process killer — multi-select with Tab, pass signal as arg (e.g. fkill -9)
if require_cmd fzf; then
  fkill() {
    local pid
    pid=$(ps -ef | sed 1d |
      fzf --tmux --multi \
        --prompt='kill > ' \
        --header 'tab: multi-select, enter: kill' | awk '{print $2}')
    [[ -n "$pid" ]] && echo "$pid" | xargs kill "${1:--15}"
  }
fi

# 1Password quick-copy — fuzzy search vault items, copy password to clipboard
if require_cmd op && require_cmd jq && require_cmd fzf; then
  fp() {
    local item
    item=$(op item list --format=json 2>/dev/null | jq -r '.[].title' |
      fzf --tmux --prompt='1password > ' \
        --header 'enter: copy password') &&
    op item get "$item" --fields label=password | wl-copy &&
    echo "Copied password for: $item"
  }
fi
