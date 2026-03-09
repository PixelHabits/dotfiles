# zshenv.d/00-logging.zsh — diagnostics infrastructure
# Runs for ALL shells. Must be silent, no subprocesses in normal mode.

: ${ZSH_BOOT_DEBUG:=0}

# Accumulated warnings for summary
typeset -ga _zsh_boot_warnings=()

zlog() {
  (( ZSH_BOOT_DEBUG )) && print -P "%F{cyan}[zsh]%f $1"
}

zwarn() {
  _zsh_boot_warnings+=("$1")
  # In interactive shells, print immediately
  if [[ -o interactive ]]; then
    print -P "%F{yellow}[zsh warn]%f $1" >&2
  fi
}

require_cmd() {
  if (( $+commands[$1] )); then
    return 0
  else
    zwarn "missing: $1"
    return 1
  fi
}
