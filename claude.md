# Claude Code

Chezmoi installs the shared Claude configuration when `dev = true`.
Work and personal profiles use the same files.
The setup supports Linux and macOS terminals, including machines without a desktop.

| Path | Purpose |
| --- | --- |
| `~/.config/claude/CLAUDE.md` | Shared instructions loaded for each conversation |
| `~/.config/claude/settings.json` | Shared configuration merged with local choices |
| `~/.local/state/claude/` | Private runtime files, history, credentials, and installed plugins |
| `~/.cache/claude/tmp/` | Disposable scratch files that survive a reboot |

Claude stores several file types in one directory.
`CLAUDE_CONFIG_DIR` points to the state directory because most of those files belong to the running application.
Two symbolic links connect that directory to the shared configuration.
Installed plugins remain in the directory that Claude manages.
See the official [environment variables](https://code.claude.com/docs/en/env-vars) and [directory reference](https://code.claude.com/docs/en/claude-directory).

`CLAUDE_CODE_TMPDIR` changes only Claude's internal scratch location.
It does not change the shell's `TMPDIR` or move existing sessions.
Claude adds its own user-specific directory below this path.
Cache cleanup can delete these files, so save lasting work in a project.

## Configuration ownership

Chezmoi sets only attribution.
Its [modify template](https://www.chezmoi.io/user-guide/manage-different-types-of-file/) preserves other keys in an existing configuration file.
Model selection, plugins, permission mode, themes, and account choices stay local.
The shell preserves an existing `DO_NOT_TRACK` privacy choice.

Project instructions belong in each project's `CLAUDE.md`.
Keep personal instructions short because Claude loads them for each conversation.
Plugin commands in those instructions apply only when that plugin is installed.

## Use an existing Claude installation

Close Claude before moving its local runtime directory.
Keep a private backup of the existing `~/.claude` directory and `~/.claude.json` file.
Do not add either backup to Git.

If Claude already contains sessions or plugins, move those local files to `~/.local/state/claude` before applying the shared configuration.
Move the old `~/.claude.json` file to `~/.local/state/claude/.claude.json` to preserve its local application state.
Copy the existing `settings.json` to `~/.config/claude/settings.json` first so the merge preserves local choices.
The two configuration links replace files with those names in the state directory.
Review those changes before applying them.
Authentication and plugin paths can depend on the old location, so sign in again or repair plugins when necessary.

Select the desired worktree with `--source` when you review the changes.
Apply only the Claude files with `--exclude scripts` to avoid running provisioning scripts.
Start a new login session so both the terminal and desktop inherit the Claude variables.
An existing shell can load `~/.config/zsh/zshenv.d/21-claude.zsh` instead.
Explicit environment overrides remain supported, but this repository deploys its files to the paths in the table.

## Test

Run `python3 tests/test_claude_config.py` from the worktree.
The tests use temporary homes and never apply files to the real home directory.
They cover local setting preservation, invalid input, repeat applies, redirects, and development-machine gating.
