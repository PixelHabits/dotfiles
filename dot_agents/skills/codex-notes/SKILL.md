---
name: codex-notes
description: Field notes on the Codex CLI and the codex-rescue handoff, measured from 230 rollouts. Sandbox geometry, what read-only denies, why git writes fail in worktrees, and what to put in a handoff prompt. Use before handing work to Codex, when a Codex run fails on a write, or when configuring Codex on a new machine.
---

# Codex notes

Each note was measured on the installed CLI when written. Re-check on a new version.

## Sandbox

- Read-only mode denies `/tmp` and `$TMPDIR` too. Nothing that compiles, tests, regenerates, or opens a shell heredoc can run. Pass `--write` for any task that runs `go build`, `go vet`, `go test`, `bun test`, `bun run generate`, `bun run check`, or `bun run typecheck`. Reserve read-only for prompts that only run `git`, `rg`, `cat`, and `sed`.
- Workspace-write grants the workspace root, `/tmp`, and `$TMPDIR`. XDG-redirected caches under `~/.cache` and `~/.local/share` are read-only, so `bun install`, `go build`, and tree-sitter fail on their first cache write. Add those cache roots to `[sandbox_workspace_write] writable_roots` in the Codex config.
- Workspace-write marks the checkout's `.git` read-only by design, and in a worktree the resolved `gitdir` as well. Codex cannot `git add` or `git commit` there. Let Codex edit; do the commit from Claude or the terminal afterward.
- A read-only run that needs a build ends with the deliverable blocked. State the mode in the prompt.

## Handoff prompt

- Codex has no conversation context. The prompt carries paths, constraints, the expected output shape, and the sandbox mode.
- Codex reads the repository `AGENTS.md` and `$CODEX_HOME/AGENTS.md`, not `CLAUDE.md`. A rule that only lives in `CLAUDE.md` does not reach it.
- Put task constraints in the prompt every time: the scope, no unasked tests, no fallbacks, no environment switches, no commits, no edits outside the named package.
- Ask for one file or one diff as the result. Do not ask Codex to page files back to you.

## Behavior seen in rollouts

- Aborted turns cluster where the prompt left the branch topology or the rebase direction implicit. Name the source branch, the target branch, and the direction.
- Codex re-reads a file from line 1 after a patch. Harmless in small files. For large files ask it to read only the edited hunk.
- Format-only `bun run check` failures get hand-patched. Say "run `bun run fix` before `bun run check`".

## Machine setup

- Codex launches MCP servers with a minimal environment. Add the XDG cache and install variables to each `[mcp_servers.*.env]` table, or the servers recreate default directories in `$HOME`.
