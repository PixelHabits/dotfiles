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
print 'PASS: current/all refs, argument forwarding, and explicit commit ID preview field'
