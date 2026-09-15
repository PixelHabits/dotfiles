# Codex configuration

If the chezmoi `dev` choice is true, chezmoi applies the Codex configuration and directory redirects.

## One file, two owners

Chezmoi owns the shared keys in `~/.config/codex/config.toml`.
Codex owns everything else in that file.
At runtime Codex writes project trust, dismissed notices, plugin state, and model picks into the same file.
Those keys never enter Git.

Edit shared preferences in `.chezmoitemplates/codex/shared.toml.tmpl`.
On apply, chezmoi reads the destination file, overwrites the shared keys, and writes the result back.
A shared MCP server replaces the destination table with the same name.
MCP servers that exist only in the destination survive.
Invalid destination TOML stops the apply without overwriting the file.

The rewrite drops comments and formatting from the destination file.

## MCP servers and XDG paths

Codex starts command-based MCP servers with a fixed environment whitelist: HOME, PATH, SHELL, USER, LANG, TERM, TMPDIR, TZ, and a few more.
It does not forward XDG variables. Without them, `bunx` writes under `~/.bun`.
Each stdio server lists the variable names it needs in `env_vars`.
When it starts the server, Codex copies those values from its own environment.
The shell and `environment.d` set the values, so no path is written into the config.

## Sandbox and approvals

The shared config sets `sandbox_mode = "danger-full-access"` and `approval_policy = "on-request"`.
With full access, Codex runs ordinary commands without asking.
It prompts only for commands it flags as dangerous, for example a recursive delete or a force push.
The value `never` would forbid those commands instead of asking, so the shared config does not use it.
`codex exec` sets `never` on its own for headless runs.

Shared MCP servers set `default_tools_approval_mode = "approve"`, so their tools run without an approval prompt.
The interactive TUI still asks to trust a directory the first time it opens one.
`codex exec` does not ask.

## Validation

Run `uv run tests/codex/test_config.py` to test the merge, the gating, and the shell redirects.
The script requires Python 3.14 or later, chezmoi, and zsh, with no Python package dependencies.
Tests use temporary homes and do not start Codex or any MCP server.
