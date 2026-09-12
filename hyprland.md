# Hyprland

Hyprland reads `~/.config/hypr/hyprland.lua` and loads `pwa.lua` from the same directory.
The configuration uses native Lua calls and requires Hyprland 0.56.2 or later.
The installed 0.56.2 parser is the tested version.
Newer versions still need the same tests before deployment.

Hypridle, Hyprlock, and Hyprlauncher keep their own configuration formats.
Shell helpers, Hypridle display commands, and Waybar scroll commands use native Lua dispatcher expressions.
Hyprland selects this IPC format, the command protocol between programs, when it loads a Lua configuration.

## Waybar compatibility

Do not deploy this configuration with Waybar 0.15.0 from the tested workstation.
Its workspace buttons send the old Hyprland command format and cannot switch workspaces under Lua.
Changing the module scroll commands does not repair its internal button handler.

Use a Waybar build that includes [the native Lua protocol fix](https://github.com/Alexays/Waybar/commit/05945748dccce28bf96d26d8f64a9e69a8dd49ba).
The installed `0.15.0-3.1` package lacks that fix.
The [upstream issue](https://github.com/Alexays/Waybar/issues/5008) records the failure.

After an upgrade, make sure that numbered and named workspace buttons work before accepting this migration.
No patched Waybar binary or package override is bundled here.

## Configuration ownership

| File | Purpose |
| --- | --- |
| `dot_config/hypr/hyprland.lua.tmpl` | Appearance, input, application commands, startup, and core shortcuts |
| `dot_config/hypr/pwa.lua.tmpl` | App shortcuts and window rules from the shared PWA catalog |
| `.chezmoidata/hyprland.toml` | Shared monitor defaults and known hardware layouts |
| Local chezmoi `data.hyprland.monitors` | Monitor override for one machine |
| `.chezmoiremove` | Retire the two old Hyprland `.conf` files on Hyprland desktops |

Lua variables hold application commands.
The startup callback launches the terminal and application menu once per session.
Configuration reloads do not launch them again.
1Password remains available through its shortcut and does not start automatically.

Monitor overrides use tables with the same names as the native monitor API:

```toml
[[data.hyprland.monitors]]
output = ""
mode = "preferred"
position = "auto"
scale = 1
```

The initialization template preserves these tables.
If you have an older comma-separated monitor override, replace it with tables before rendering this configuration.
The [monitor API](https://wiki.hypr.land/Configuring/Basics/Monitors/) lists the available fields.

## First deployment

The running compositor selects its configuration format at startup.
A reload does not switch the configuration manager from Hyprlang to Lua.
The [0.56.2 configuration manager](https://github.com/hyprwm/Hyprland/blob/v0.56.2/src/config/ConfigManager.cpp) defines this behavior.

Save your work and sign out of Hyprland before the first deployment.
From a text console, review the selected source:

```sh
chezmoi --source ~/.local/share/chezmoi/hyprland-lua-config --exclude scripts diff
```

Make sure that the diff includes the two Lua files and the retirement of `hyprland.conf` and `pwa.conf`.
Apply the desktop files and all helpers together:

```sh
chezmoi --source ~/.local/share/chezmoi/hyprland-lua-config --exclude scripts apply \
  ~/.config/hypr/hyprland.lua \
  ~/.config/hypr/pwa.lua \
  ~/.config/hypr/hypridle.conf \
  ~/.config/hypr/hyprland.conf \
  ~/.config/hypr/pwa.conf \
  ~/.config/waybar/config.jsonc \
  ~/.local/bin/hypr-workspace-app \
  ~/.local/bin/hypr-rescue \
  ~/.local/bin/omarchy-hyprland-window-pop \
  ~/.local/bin/omarchy-hyprland-window-close-all \
  ~/.local/bin/omarchy-hyprland-workspace-layout-toggle
```

Start a new Hyprland session.
For later Lua changes, use the routine update steps in [PWA configuration](pwa.md#review-and-deploy).
Do not pass `--config hyprland.conf` in a custom startup command.

## Validation

Run the tests from this worktree:

```sh
python3 tests/hyprland.py
python3 tests/hyprland_deployment.py
python3 tests/hyprland_ipc.py
python3 tests/pwa.py
python3 tests/test_suspend_templates.py
python3 tests/test_hypr_rescue.py
```

The tests require Python 3.11 or later, Lua, chezmoi, Bash, and jq.
When Hyprland is installed, the tests run its parser against temporary files.
The tests capture Lua declarations without executing their commands.
They compare all 102 core bindings and their flags with the preserved configuration.
They also cover provider choices, five PWA bindings, monitor overrides, startup commands, and window rules.
Helper tests capture IPC requests and pass the dispatcher constructors to the native parser without executing them.
No test applies configuration to the live home directory or starts a graphical session.
Native parsing confirms accepted syntax, not display hardware or keyboard behavior.

The [0.56.2 dispatcher implementation](https://github.com/hyprwm/Hyprland/blob/v0.56.2/src/config/lua/bindings/LuaBindingsDispatchers.cpp) defines the action mappings.
See [suspend recovery](suspend-recovery.md) for the separate hardware acceptance tests.
