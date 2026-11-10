# App workspaces

Each app category opens on its own Hyprland workspace.
A web provider opens as a Helium or other Chromium `--app` window, without browser tabs.
A desktop provider runs its own command.

## Shortcuts

Hold Super and Shift, then press the category key.

| Key | Category | Workspace |
| --- | --- | --- |
| A | AI chat | `ai` |
| E | Mail | `mail` |
| M | Music | `music` |
| L | Projects | `projects` |
| T | Messages | `messages` |
| G | Repositories (GitHub) | `repos` |
| C | Coding agents (T3 Code) | `agents` |
| N | Editor | Current workspace |

Each shortcut shows the app's workspace and opens the app only when its window is not already there.
Super + L locks the session.
Workspace names name the category, never a provider, so they stay the same when the provider changes.

## Machine choices

`chezmoi init` asks Hyprland machines to choose providers for AI chat, Mail, Music, Projects, and Messages.
It also asks for the Projects and Repositories landing URLs.
Use a public home page, organization page, or repository page without query parameters.
These answers stay in the local chezmoi configuration.
Shared definitions contain no email address, account ID, or organization name.

Each key starts with the workspace name.
To change a choice, edit the existing `[data]` table in `~/.config/chezmoi/chezmoi.toml`:

```toml
ai_provider = "claude"
mail_provider = "outlook"
music_provider = "youtube"
projects_provider = "linear"
messages_provider = "slack"
projects_url = "https://linear.app"
repos_url = "https://github.com"
```

When changing the Projects provider, set its landing URL to a page on that provider's domain.
Nothing is preselected. Until a machine has every answer, `chezmoi apply` stops and names the missing key; run `chezmoi init` to answer it.
Initialization preserves saved choices.
Machines without Hyprland save no app choices.
The browser handles authentication after launch.

## Coding agents

Super + Shift + C and the `agents` workspace exist only when `chezmoi init` marked the machine as a development machine.
Its one provider, T3 Code, comes from the AUR package `t3code-dev`, which provides the `t3code` command.
Ansible does not install it.

## Add a provider

Add a table under the category in `.chezmoidata/apps.toml`:

```toml
[apps.messages.providers.slack]
url = "https://app.slack.com"
```

A web provider needs only its public `url`. Its window rule matches the URL's host.
A desktop provider sets `command` and a window `class` regex instead.
A provider can set its own `icon`, which replaces the category icon in the bar.
A category with more than one provider asks which one at `chezmoi init`.
