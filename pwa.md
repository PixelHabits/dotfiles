# Web app workspaces

A web app opens a website in a browser window without tabs, on a dedicated Hyprland workspace.
It runs through Helium or another Chromium browser that supports `--app`.

## Shortcuts

Hold Super and Shift, then press the app key.

| Key | App | Workspace |
| --- | --- | --- |
| A | T3 Chat | `chat` |
| E | Mail | `mail` |
| M | Music | `music` |
| L | Linear | `linear` |
| T | Teams | `teams` |

Super + L still locks the session.
Shift+L is the Linear bind.

## Mail provider and Linear URL

`chezmoi init` prompts Hyprland machines for a mail provider and a Linear landing URL.
Other machines use the `work`/`personal` profile default in `.chezmoidata/pwa.toml`.
Override either on one machine in the existing `[data]` table of `~/.config/chezmoi/chezmoi.toml`:

```toml
mail_provider = "gmail"
linear_url = "https://linear.app/another-workspace"
```

## Add an app

Add an entry under `pwa.apps` in `.chezmoidata/pwa.toml`, and its workspace name to `pwa.order`.
Fields: `label` (display name), `key` (shortcut key), `icon` (Waybar icon), `url` (site to open), `class` (regex matched against the browser window class).
