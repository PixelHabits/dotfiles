# Codex configuration

Development machines share Codex preferences on both work and personal profiles.
The configuration also works without a desktop.
Chezmoi does not install Codex or sign in to an account.

## Shared and local values

Edit shared preferences in `.chezmoitemplates/codex/shared.toml.tmpl`.
Chezmoi combines them with the existing `~/.config/codex/config.toml`.
Shared keys take precedence. Other keys remain local.
This preserves trusted projects, untrusted projects, local tools, and plugin metadata.
A new machine starts without trusted projects.

The template parses TOML, the configuration file format.
It rewrites formatting and removes comments from the destination file.
Invalid TOML stops the update before chezmoi overwrites that file.
Do not use `chezmoi add` or `chezmoi re-add` on the generated configuration.
Those commands can replace the template with local paths or credentials.

Optional overrides live in `~/.config/codex/local.config.toml`.
Chezmoi leaves that file alone.
When that file exists, the Zsh alias selects it with `--profile local`.
A new machine without that file uses the shared base configuration.
For GUI or direct binary launches, select a profile explicitly when you need those overrides.
Codex profile files require Codex 0.134.0 or later.

## Directories and local tools

`CODEX_HOME` remains `~/.config/codex`.
Codex keeps configuration, authentication, sessions, and some caches together in that directory.
Logs and SQLite state use `~/.local/state/codex`.
This setup does not move existing sessions, credentials, or databases.
Codex does not provide separate XDG paths for every artifact.

MCP connects Codex to external tools.
Codex filters environment variables before it starts a local MCP process.
The template supplies XDG, Go, Bun, and npm paths to every command-based server in the base configuration.
Explicit environment values already set on a server take precedence over these defaults.
Shell exports alone do not cross that process boundary.

The defaults keep Go downloads, Bun packages, and npm caches out of the home directory root.
They apply when the server starts, including when Codex starts it before a shell runs.
Servers from profiles, project configuration, or plugins can define separate environments.
Set the same redirects in those server definitions if they launch package tools.
The setup does not rewrite third-party plugin files or delete existing home directories.
Chrome DevTools requires a browser when you use its tools.

## Review and tests

Review from the feature worktree without changing the live home directory:

```sh
chezmoi --source ~/.local/share/chezmoi/codex-config diff ~/.config/codex/config.toml
python3 ~/.local/share/chezmoi/codex-config/tests/codex/test_config.py
```

The tests require Python 3.11+, chezmoi, Zsh, and Codex.
They use temporary home directories and no credentials.
They test repeated updates, local trust, invalid TOML, profile selection, and development-machine gating.
A local MCP fixture also tests the environment received from the installed Codex process.
The fixture replaces real servers and points the model provider at an unused localhost port.
It does not test account access, real tools, or a desktop browser.

## References

- [OpenAI configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference)
- [OpenAI profile files and state locations](https://learn.chatgpt.com/docs/config-file/config-advanced)
- [OpenAI MCP configuration](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)
- [Bun package cache](https://bun.com/docs/pm/global-cache)
