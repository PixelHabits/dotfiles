---
name: claude-code-notes
description: Field notes on the Claude Code harness, measured from five weeks of session logs. Shell working directory, tool shell, output caps, deferred tools, worktree guard, auto-mode classifier, hooks, subagent and workflow costs. Use when a tool call fails oddly, before spawning agents or workflows, when a command is refused, or when setting up Claude Code on a new machine. Verify against the installed version.
---

# Claude Code harness notes

Each note was measured on the installed build when written. Re-check any of them on a new version before relying on it.

## Shell

- The Bash tool runs the login shell. On zsh, an unmatched glob (`--include=*.ts`) and a word starting with `=` (`echo ===`) abort the command before it runs. The fix is `CLAUDE_CODE_SHELL=/bin/bash` in the environment, not a quoting habit. Confirm with `ps -o comm= -p $$`.
- Under bash the tool shell has no `globstar`: `**` matches one level and reports nothing. Use `find` or `rg` for recursion. Pipe status is `${PIPESTATUS[0]}`.
- The working directory persists between calls while it stays inside the session root, and resets to the root only after a command that ends outside it. A bare `cd apps/web` therefore moves every later call. The setting `CLAUDE_BASH_MAINTAIN_PROJECT_WORKING_DIR=1` in `settings.json` `env` restores the root after every call.
- `GIT_EDITOR=true` is already exported into every tool shell by the binary. `git rebase --continue` and `--autosquash` need no prefix.
- Bash output is cut at 30,000 characters and the rest is saved to a file. Read carries about 100 KB per call. The `bashOutputMaxChars` setting raises the Bash cap. Never `cat` several files into one output.
- A foreground Bash call dies at 10 minutes. Never wait for a deploy, a CI run, or a Codex job inside a loop.

## Permissions and guards

- In auto mode every Bash call that no allow rule matches goes to a classifier model. Narrow allow rules (`Bash(bun run typecheck*)`, `Bash(bun x ultracite *)`, `Bash(bun test *)`) resolve at once. `sed` is not in the built-in read-only set, so `sed -n` reads go to the classifier; use Read.
- When the classifier model is rate-limited the call is refused, not prompted. Retry once after a pause.
- `EnterWorktree` installs a static guard that refuses any command with a heredoc, `$(...)`, a loop, a glob, or a relative `cd`, and refuses edits in sibling worktrees. Do not use it. Launch a session inside the worktree instead.
- Route files with `$` in the name (`$entryId.tsx`) go to Read, Edit, and Write unescaped. Quote them only in Bash.

## Hooks

- PostToolUse stdout and stderr on a non-blocking exit never reach the model. Only `hookSpecificOutput.additionalContext` does. A red hook notice is for the human.
- A PostToolUse formatter without a file argument scans the whole tree on every edit. Read the edited path from the hook stdin JSON (`jq -r .tool_input.file_path`) and format that file only.
- After `git reset`, `git checkout -- <file>`, a rebase, or a Bash edit (`sed -i`, heredoc), Read the file before the next Write or Edit, or the harness rejects the write as stale.
- SessionStart hook output is loaded into every session. Plugins that inject rule blocks cost thousands of tokens per call. Keep only the ones whose rules are wanted in every session.

## Deferred tools

- WebFetch, WebSearch, SendMessage, Monitor, and TaskStop are deferred. Each first use costs a ToolSearch round trip that resends the whole context. Fetch the set you will need in one call: `select:WebFetch,WebSearch,SendMessage`.
- MCP servers add their tool names to every call. Remove servers a project no longer uses.

## Subagents and workflows

- A fork inherits the full parent context on every one of its turns. Use fork only when the task needs conversation state that is not written down. With a brief file, launch general-purpose or codex-rescue and pass the path.
- A subagent starts in the parent's current shell directory. Name the absolute worktree path in the first line of its prompt.
- Every writing subagent needs its own worktree (`isolation: 'worktree'`), or it will edit a checkout another session owns.
- Cross-session SendMessage costs a full turn on the receiver and peer names change on restart. Write decisions to a file the peers read. Call ListAgents before sending to a name not seen this turn.
- A workflow that maps one verifier per raw item can exhaust the spend limit; `parallel()` turns each failure into `null` and keeps going. Filter and cluster first, cap the fan-out, check the first batch before launching the rest, and treat a spend-limit or 429 result as a stop.
- StructuredOutput: required fields are exactly the fields the script reads, every required key is named in the prompt, long prose goes to a file and the schema carries the path. Reject outputs whose fields read "test" or "TODO".
- A subagent that stops on an expired MCP token resumes by itself after re-authorization. Wait for its next notification. Do not redo its steps.

## Context budget

- Everything in `CLAUDE.md`, the memory index, the skill listing, deferred tool names, MCP instructions, and SessionStart hook output rides on every API call. Measure with the first lines of a session transcript. Disable plugins whose skills and tools go unused, keep the memory index under 10 KB, keep instruction files to invariants.
