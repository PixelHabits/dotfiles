# zshrc.d/10-history.zsh — canonical history policy

# History is state, not config — use XDG_STATE_HOME
[[ -d "$XDG_STATE_HOME/zsh" ]] || mkdir -p "$XDG_STATE_HOME/zsh"

HISTFILE="$XDG_STATE_HOME/zsh/history" # history file path
HISTSIZE=100000         # number of history entries kept in memory
SAVEHIST=100000         # number of history entries saved to HISTFILE

setopt inc_append_history   # append each command to HISTFILE as soon as it is entered
setopt hist_ignore_dups     # do not add a command if it duplicates the previous history entry
setopt hist_ignore_all_dups # remove the older entry when a new command duplicates any previous one
setopt hist_save_no_dups    # omit older duplicate commands when writing the history file
setopt hist_reduce_blanks   # remove extra blanks from commands before saving them to history

setopt hist_ignore_space    # do not keep commands that begin with a space in history
setopt hist_no_store        # do not store the fc -l history command in the history list

zshaddhistory() { whence ${${(z)1}[1]} >| /dev/null || return 1 } # skip saving history entries whose first word is not a known command

