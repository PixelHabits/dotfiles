# Claude Code

Claude Code reads these paths:

| Path | Purpose |
| --- | --- |
| `~/.config/agents/AGENTS.md` | Instructions shared by every agent. Claude imports it, Codex reads it through a link |
| `~/.config/claude/CLAUDE.md` | The import plus Claude-only instructions, loaded for each conversation |
| `~/.agents/skills/` | Skill folders that every agent loads on demand |
| `~/.config/claude/settings.json` | Shared configuration merged with local choices |
| `~/.local/state/claude/` | Private runtime files, history, credentials, and installed plugins |
| `~/.local/state/claude/tmp/` | Active scratch work that survives reboots and cache cleanup |

## Design

Claude stores several file types in one directory.
`CLAUDE_CONFIG_DIR` points at the state directory because most of those files are runtime state, not configuration.
Two symlinks bridge that directory back to the shared configuration above: one for `CLAUDE.md`, one for `settings.json`.

`CLAUDE_CODE_TMPDIR` changes only Claude's internal scratch location.
Claude appends its own per-user subdirectory below this path.

See the official [environment variables](https://code.claude.com/docs/en/env-vars) and [directory reference](https://code.claude.com/docs/en/claude-directory) pages.

## Test

Run `uv run tests/test_claude_config.py` to test settings in a temporary home.

## One project per repository

Claude stores transcripts and auto memory under a project directory named after the working directory.
A repository with many worktrees therefore gets one project directory per worktree.
Memory written in one worktree stays invisible in the others.

`~/.local/bin/claude` is a small launcher in front of the real `claude` binary.
It resolves the canonical Git common directory and hashes that path with Git.
The store name combines a readable repository basename with the full digest.
Names use only letters, digits, hyphens, and underscores.
The readable part is limited to 48 characters.
Git computes the digest without writing an object or changing the repository.
When `CLAUDE_CONFIG_DIR` is set, the launcher exports `CLAUDE_CODE_PROJECT_DIR_NAME` and then runs the next `claude` on `PATH`.
Every worktree of one repository then shares one project directory.
Outside a repository, or when `CLAUDE_CONFIG_DIR` is unset, the launcher changes nothing.
A name you export yourself wins.
Claude accepts names made of letters, digits, hyphens, and underscores only, and falls back to the derived name otherwise.
See the official [session storage](https://code.claude.com/docs/en/sessions#name-the-project-directory-yourself) notes.

Two launch habits follow from this:

| Work | Start here |
| --- | --- |
| Build or edit one branch | `cd <root>/<feature> && claude` |
| Orchestrate or review across branches | `cd <root> && claude` |

A session started inside a worktree keeps that worktree as its root.
The shared configuration sets `CLAUDE_BASH_MAINTAIN_PROJECT_WORKING_DIR=1`, so every tool shell call starts at that root.
It also denies the `EnterWorktree` tool, whose command guard refuses ordinary shell syntax.
Start a new session in the other worktree instead.

Claude reads `CLAUDE.md` from parent directories.
A container `CLAUDE.md` with the single line `@AGENTS.md` loads the container rules from any worktree.
`worktrees.md` shows the command.

Unrelated repositories with matching basenames receive different automatic store names.
Symbolic links to the same repository resolve to the same identity.
Moving a repository or changing its Git object format changes its automatic store name.
An explicit `CLAUDE_CODE_PROJECT_DIR_NAME` keeps a chosen name stable across such changes.
The launcher does not move existing transcripts or memory.
Keep a private backup and close Claude before moving any existing project files.
Choose each source directory explicitly and preserve files with matching names for manual comparison.
