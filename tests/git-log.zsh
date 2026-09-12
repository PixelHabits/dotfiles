#!/usr/bin/env zsh
set -eu
require_cmd() { [[ "$1" == git || "$1" == fzf ]]; }
git() { print -r -- "$*"; }
fzf() { cat; print -r -- "$*"; }
source "${0:A:h:h}/dot_config/zsh/zshrc.d/41-functions.zsh"
result=$(fgl)
[[ "$result" != *--all*' --all'* ]]
[[ "$result" == *'--format=%H%x09%C(auto)%h %s%d'* ]]
[[ "$result" == *'git show --color=always --stat {1} --'* ]]
[[ "$result" != *'grep -oE'* ]]
[[ "$(fgl --all HEAD~2)" == *'--all HEAD~2'* ]]
[[ "$(fgl -a HEAD~2)" == *'--all HEAD~2'* ]]
[[ "$(fgl -- src)" == *'-- src'* ]]
for option in --format=%s --pretty=raw --oneline --graph --stat --definitely-invalid; do
  if fgl "$option" >/dev/null 2>&1; then
    print -u2 "accepted unsafe output option: $option"
    exit 1
  fi
done
git() { return 17; }
if fgl >/dev/null; then exit 1; else [[ $? == 17 ]]; fi
git() { return 141; }
fzf() { return 130; }
fgl
print 'PASS: current/all refs, argument forwarding, stable ID field, rejected presentation flags, errors and cancellation'
