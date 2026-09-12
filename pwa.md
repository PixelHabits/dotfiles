# Web app workspaces

A web app opens a website in a browser window without tabs.
These apps use Helium through the Hyprland `browser` setting.
Another Chromium browser must support `--app` and compatible window classes.
This setup does not install browser extensions or synchronize accounts.

## Shortcuts

Hold Super and Shift, then press the app key:

| Key | App | Workspace |
| --- | --- | --- |
| A | T3 Chat | `chat` |
| E | Mail | `mail` |
| M | Music | `music` |
| L | Linear | `linear` |
| T | Teams | `teams` |

The shortcut selects the named workspace.
If that workspace is visible on another monitor, the shortcut focuses that monitor.
If the workspace contains the matching app, the launcher does not open another window.
Otherwise, it opens the app.
If you move the app to another workspace, the shortcut can open another window in its assigned workspace.
Super + L still locks the session.

## Choose services for a machine

The profile supplies defaults when the machine does not contain an explicit choice:

| Profile | Mail | Linear |
| --- | --- | --- |
| `work` | Outlook | Greenway Automotive |
| `personal` | Gmail | Linear home |

On Hyprland, initialization asks for the mail provider and Linear landing URL.
Your answers stay in the local chezmoi configuration.
A work machine can choose Gmail, and a personal machine can choose Outlook.
Existing machines use the profile defaults until you select explicit values.
Once saved, explicit values stay the same if you later change the profile.

In `~/.config/chezmoi/chezmoi.toml`, add or change these keys inside the existing `[data]` section:

```toml
mail_provider = "gmail"
linear_url = "https://linear.app/another-workspace"
```

Do not add a second `[data]` section.
The Linear URL must use `https://linear.app` with an optional workspace path.
Query parameters and fragments are not accepted.
The browser uses its current profile and signed-in accounts.
A different mail provider does not create a separate browser profile.

## Review and deploy

Before you start, read [source selection](worktrees.md#select-the-live-source).
For the first switch from `.conf` to Lua, follow [Hyprland deployment](hyprland.md#first-deployment) before this routine update.
Select the worktree that contains the changes you want to test.

Review all four deployment targets:

```sh
chezmoi --source ~/.local/share/chezmoi/hyprland-lua-config diff \
  ~/.config/hypr/hyprland.lua \
  ~/.config/hypr/pwa.lua \
  ~/.config/waybar/config.jsonc \
  ~/.local/bin/hypr-workspace-app
```

The diff compares the selected worktree with your live files.
Review all differences before you apply the Hyprland or Waybar configuration.
For a trial with no Ansible run, use the same targets:

```sh
chezmoi --source ~/.local/share/chezmoi/hyprland-lua-config --exclude scripts apply \
  ~/.config/hypr/hyprland.lua \
  ~/.config/hypr/pwa.lua \
  ~/.config/waybar/config.jsonc \
  ~/.local/bin/hypr-workspace-app
hyprctl reload
pkill -USR2 -x waybar
```

These commands change your live desktop files.
They do not change the default `sourceDir`.

## Maintain the definitions

| File | Responsibility |
| --- | --- |
| `.chezmoidata/pwa.toml` | App definitions, provider URL and class pairs, and profile defaults |
| `.chezmoi.toml.tmpl` | Prompts and saved machine choices |
| `.chezmoitemplates/pwa-apps.json` | Select the provider and resolve the app list |
| `dot_config/hypr/pwa.lua.tmpl` | Generate shortcuts and window rules |
| `dot_config/waybar/config.jsonc.tmpl` | Generate workspace icons |
| `dot_local/bin/executable_hypr-workspace-app` | Focus or open the app |

To add a mail provider, add its URL and window class pattern under `pwa.mailProviders`.
The initialization prompt uses the provider names from that table.
Use `hyprctl clients -j` to inspect the class of its app window.
Make sure that the pattern matches the app, then run the tests.

## Tests

Run `python3 tests/pwa.py` from this worktree.
The tests need Python 3.11 or later, chezmoi, Bash, and jq.
If Hyprland is installed, the tests also parse the generated app configuration with Hyprland.
The tests use temporary files and fake desktop commands.
They do not open websites or apply files to your home directory.
Browser sign-in and actual window creation still need a desktop trial.
