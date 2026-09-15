---
name: codex-notes
description: Field notes on the Codex CLI and the codex-rescue handoff, measured from 230 rollouts. Sandbox geometry, what read-only denies, why git writes fail in worktrees, and what to put in a handoff prompt. Use before handing work to Codex, when a Codex run fails on a write, or when configuring Codex on a new machine.
---

# Codex notes

Each note was measured on the installed CLI when written. Re-check on a new version.

## Sandbox

- Measured read-only runs denied scratch writes. Builds, tests, codegen, and heredocs can need them. Choose `--write` when the task authorizes writes; use read-only for inspection. Check effective permissions and required paths before launch. Do not silently widen a read-only assignment.
- The writable root is the directory the thread starts in, which the codex-rescue plugin takes from the Claude session's cwd. In the bare layout every other worktree is a sibling, so it is outside the root and writes there are refused. Start the thread in the worktree it edits: `codex-companion.mjs task --cwd <worktree>` or `codex exec -C <worktree>`. Never point a thread at a container or a parent directory to reach several worktrees.
- Workspace-write grants that root, `/tmp`, and `$TMPDIR`. XDG-redirected caches under `~/.cache` and `~/.local/share` are read-only, so `bun install`, `go build`, and tree-sitter fail on their first cache write. Add those cache roots to `[sandbox_workspace_write] writable_roots` in the Codex config.
- Workspace-write marks the checkout's `.git` read-only by design, and in a worktree the resolved `gitdir` as well. Normal sandbox writes cannot `git add` or `git commit` there. Approval and host policy can differ. If blocked, report it; leave the commit to the parent or terminal.
- A read-only run that needs a build ends with the deliverable blocked. State the mode in the prompt.

## Plugin commands and completion

- Discover the installed Codex plugin root. Read its command and agent files before use; versions can change this contract.
- Slash commands with `disable-model-invocation: true` are user-only. Do not call them through Skill. For an authorized review, use the discovered `scripts/codex-companion.mjs` runtime and the review command's documented arguments.
- `codex:codex-rescue` forwards `task` only. It does not monitor, review, or collect results. Parent owns follow-up. Do not ask rescue to run status or result.
- Background enqueue returns a job ID before work finishes. Keep that ID and the same cwd, `CLAUDE_PLUGIN_DATA`, and `CODEX_COMPANION_SESSION_ID` environment. Do not guess paths or poll a different session.
- Run `node "<plugin-root>/scripts/codex-companion.mjs" status <job-id> --json`. `queued` and `running` mean wait. For `completed`, `failed`, or `cancelled`, run `result <job-id> --json` through the same script.
- Read `job.status`, `storedJob.result`, and any error fields. Even a failed job's `result` command can exit zero. Launch exit zero, wrapper completion, and empty output do not prove success. Report malformed output, failed startup, or missing result as incomplete.
- Compare the final result with requested deliverables and inspect claimed edits or tests. Do not turn a started job into a completed review.

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
