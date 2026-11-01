# Hyprland

Hyprland reads `~/.config/hypr/hyprland.lua` and loads `pwa.lua` from the same directory.
The configuration uses native Lua calls and requires Hyprland 0.57.0 or later.

Hypridle, Hyprlock, and Hyprlauncher keep their own configuration formats.
Hypridle display commands and Waybar scroll commands send native Lua dispatcher expressions.
Hyprland selects this IPC format, the command protocol between programs, when it loads a Lua configuration.

## Desktop actions

Window pop-out, close all windows, and screenshots run as Lua functions inside Hyprland.
They read windows and monitors through the Hyprland query API and act through its dispatchers.
If Hyprland refuses an action, for example a pin on a fullscreen window, a Hyprland notification shows the reason.

Screenshots use `grim` and `slurp`.
Each screenshot goes to `$HYPRSHOT_DIR` or the XDG pictures folder and to the clipboard, and a notification names the file.
Window and region screenshots freeze the screen with `hyprpicker` while you select.

## Configuration ownership

| File | Purpose |
| --- | --- |
| `dot_config/hypr/hyprland.lua.tmpl` | Monitors per machine, appearance, input, application commands, startup, core shortcuts, and desktop actions |
| `dot_config/hypr/pwa.lua.tmpl` | App shortcuts and window rules from the shared PWA catalog |
| `.chezmoiremove` | Retire the old Hyprland `.conf` file and the replaced helper scripts on Hyprland desktops |

Lua variables hold application commands.
The startup callback launches the terminal and application menu once per session.
Configuration reloads do not launch them again.

## Validation

Run the test from the repository checkout:

```sh
uv run tests/hyprland.py
```

It requires uv with Python 3.14 or later, Lua, chezmoi, and Hyprland.
It renders the config for each machine named in the template and for an unlisted machine, then runs Hyprland's own parser on each.
It also runs the region screenshot command with stand-in tools to confirm the screen stays frozen until the capture.
Nothing is applied to the live home directory, and no graphical session starts.
Parsing confirms accepted syntax, not display hardware or keyboard behavior.
