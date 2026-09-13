# Web app workspaces

A web app opens a website without browser tabs, on a dedicated Hyprland workspace.
Helium or another Chromium browser supplies the `--app` window.

## Shortcuts

Hold Super and Shift, then press the category key.

| Key | Category | Workspace |
| --- | --- | --- |
| A | AI Chat | `chat` |
| E | Mail | `mail` |
| M | Music | `music` |
| L | Projects | `linear` |
| T | Messages | `teams` |
| G | GitHub | `github` |
| N | Editor | Current workspace |

Super + L locks the session.
Workspace names stay stable when the provider changes.

## Machine choices

`chezmoi init` asks Hyprland machines to choose providers for AI Chat, Mail, Music, Projects, and Messages.
It also asks for the Projects and GitHub landing URLs.
Use a public home page, organization page, or repository page without query parameters.
These answers stay in the local chezmoi configuration.
Shared definitions contain no email address, account ID, or organization name.

To change a choice, edit the existing `[data]` table in `~/.config/chezmoi/chezmoi.toml`:

```toml
ai_provider = "claude"
mail_provider = "outlook"
music_provider = "youtube"
project_provider = "linear"
chat_provider = "slack"
project_url = "https://linear.app"
github_url = "https://github.com"
```

When changing the Projects provider, set its landing URL to a page on that provider's domain.
Initialization preserves saved choices.
The browser handles authentication after launch.

## Add a provider

Add its public `host` and `url` under `pwa.providers.<workspace>` in `.chezmoidata/pwa.toml`.
The resolver generates the matching window class from the same host.
The provider then appears in the initialization choices.
Chezmoi include files use `.tmpl` because their contents are templates.

Run `uv run tests/pwa.py` to render the machine variants without opening an app.

For the first switch to Lua, follow [Hyprland deployment](hyprland.md#first-deployment).
