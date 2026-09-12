# Claude Code

Chezmoi installs the shared Claude configuration when `dev = true`.
Work and personal profiles use the same files.
The setup supports Linux and macOS terminals, including machines without a desktop.
If a host provider manages the agent directories, set `agent_home_managed = true` in the local chezmoi `[data]` table.
This skips the Claude configuration, runtime links, and redirects so provider updates continue to reach the files that Claude reads.
The default is `false`, and `chezmoi init` preserves the choice without another prompt.
Choose this before the first apply on a provider-managed host.
Changing it later does not remove old redirect files or alter the environment of running sessions.
Before handing an existing installation to a provider, remove the old Claude redirect files and start a new login session.

| Path | Purpose |
| --- | --- |
| `~/.config/claude/CLAUDE.md` | Shared instructions loaded for each conversation |
| `~/.config/claude/settings.json` | Shared configuration merged with local choices |
| `~/.local/state/claude/` | Private runtime files, history, credentials, and installed plugins |
| `~/.local/state/claude/tmp/` | Active scratch work that survives reboots and cache cleanup |

Claude stores several file types in one directory.
`CLAUDE_CONFIG_DIR` points to the state directory because most of those files belong to the running application.
Two symbolic links connect that directory to the shared configuration.
Installed plugins remain in the directory that Claude manages.
See the official [environment variables](https://code.claude.com/docs/en/env-vars) and [directory reference](https://code.claude.com/docs/en/claude-directory).

`CLAUDE_CODE_TMPDIR` changes only Claude's internal scratch location.
It does not change the shell's `TMPDIR` or move existing sessions.
Claude adds its own user-specific directory below this path.
Scratch files can contain unfinished work and Git worktrees, so this setup never deletes them automatically.
Remove scratch files only after the sessions that use them finish.
The state directory must live on persistent storage for work to survive a reboot.
The redirect does not promise persistence for every child process's temporary file.

`CLAUDE_CODE_SHELL` selects `/bin/bash` for Claude tool commands on Linux and macOS.
The interactive shell remains Zsh.
Bash inherits the exported XDG paths from the Claude process, so it does not need to load Zsh configuration.
The shell fallback preserves an explicit `CLAUDE_CODE_SHELL` override.

## Configuration ownership

Chezmoi sets only attribution.
Its [modify template](https://www.chezmoi.io/user-guide/manage-different-types-of-file/) preserves other keys in an existing configuration file.
Model selection, plugins, permission mode, themes, and account choices stay local.
The shell preserves an existing `DO_NOT_TRACK` privacy choice.

Project instructions belong in each project's `CLAUDE.md`.
Keep personal instructions short because Claude loads them for each conversation.
Plugin commands in those instructions apply only when that plugin is installed.

## Memory across machines

Use a separate memory directory for each project.
In that project's `.claude/settings.json`, set `autoMemoryDirectory` to a stable path such as `~/.local/share/claude/memory/example-project`.
Claude applies this project setting after workspace trust.
Do not set one global memory directory or project-name override for unrelated repositories.
See the supported [memory directory setting](https://code.claude.com/docs/en/settings-reference#automemorydirectory).

Directory selection does not synchronize files between machines.
Keep company memory in a private repository or another approved company storage location.
This dotfiles repository does not create a memory repository, copy memory files, or add automatic Git synchronization hooks.

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
Existing sessions can reference absolute scratch paths.
Before a reboot, preserve any active scratch directories separately and restore their original paths before resuming those sessions.
Changing the redirect affects new scratch files and does not rewrite old session references.

Select the desired worktree with `--source` when you review the changes.
Apply only the Claude files with `--exclude scripts` to avoid running provisioning scripts.
Start a new login session so both the terminal and desktop inherit the Claude variables.
An existing shell can load `~/.config/zsh/zshenv.d/21-claude.zsh` instead.
Explicit environment overrides remain supported, but this repository deploys its files to the paths in the table.

## Test

Run `python3 tests/test_claude_config.py` from the worktree.
The tests use temporary homes and never apply files to the real home directory.
They cover local setting preservation, invalid input, repeat applies, shell inheritance, redirects, and machine gating.
If Claude is installed, a local test plugin makes sure that native configuration writes preserve the symbolic link.
The test uses no account and downloads no plugins.
