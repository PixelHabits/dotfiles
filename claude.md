# Claude Code

Claude Code reads these paths:

| Path | Purpose |
| --- | --- |
| `~/.config/claude/CLAUDE.md` | Shared instructions loaded for each conversation |
| `~/.config/claude/settings.json` | Shared configuration merged with local choices |
| `~/.local/state/claude/` | Private runtime files, history, credentials, and installed plugins |
| `~/.local/state/claude/tmp/` | Active scratch work that survives reboots and cache cleanup |

## Agent-managed hosts

When a host image already manages the agent directories, set `agent_home_managed = true` in the local chezmoi `[data]` table.
This skips the Claude configuration, runtime links, and redirects so provider updates keep reaching the files Claude reads.
The default is `false`.
Choose this before the first apply on such a host.
Flipping it later does not clean up files an earlier apply already wrote.

## Design

Claude stores several file types in one directory.
`CLAUDE_CONFIG_DIR` points at the state directory because most of those files are runtime state, not configuration.
Two symlinks bridge that directory back to the shared configuration above: one for `CLAUDE.md`, one for `settings.json`.

`CLAUDE_CODE_TMPDIR` changes only Claude's internal scratch location.
Claude appends its own per-user subdirectory below this path.

See the official [environment variables](https://code.claude.com/docs/en/env-vars) and [directory reference](https://code.claude.com/docs/en/claude-directory) pages.
