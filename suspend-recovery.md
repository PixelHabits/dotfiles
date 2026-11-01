# Hyprland display recovery

Hypridle locks the session before sleep and wakes the displays after resume.
It waits for the session lock with `inhibit_sleep = 3`.
It does not use a fixed delay as proof that the lock is ready.

`allow_session_lock_restore` permits a replacement locker if the original locker crashes.
The recovery helper does not kill or restart the locker.

## Laptop lid

On GAM-DEV001, closing the lid disables the internal panel, so the laptop can run closed with external displays.
Opening the lid while awake reloads the monitor configuration.
A lid opened during suspend sends no event, because the input devices are unavailable.
After resume, Hypridle on laptops reads the ACPI lid state from `/proc/acpi/button/lid/*/state` and reloads the configuration if the lid is open.
GAM-DEV001 reports the state at `/proc/acpi/button/lid/LID/state`.

The lid binds and the internal panel name sit in the GAM-DEV001 monitor block of `dot_config/hypr/hyprland.lua.tmpl`.
Other machines use the preferred mode for each connected display and get no lid binds.
Desktop machines do not get the ACPI check.

## Dock workflow

Open the lid before you connect the dock.
If the dock is connected while the laptop is asleep with the lid closed, the internal panel releases its display pipe.
The compositor's restore after resume is then rejected.
This is an Aquamarine defect: restore does not read the kernel's connector routing.
This configuration does not fix it.

## Recover a display

`hypr-rescue` reloads the configured monitors and requests display power.
It preserves the lock screen and does not activate another login session.
It accepts a signature, the unique name of a running Hyprland instance.

From a terminal in the affected session, run:

```sh
hypr-rescue
```

From a text console, list the instances first:

```sh
hyprctl instances
hypr-rescue INSTANCE_SIGNATURE
```

Return to the affected graphical session and unlock normally.
From a text console, the helper reparses the configuration and requests display power.
The display restore applies when you return to the graphical session.
Session activation makes Hyprland reload and apply the monitor configuration.
Instance discovery has a five-second timeout.
Reload and display-power requests each have a twenty-second timeout for docked monitors.
The helper does not claim success beyond acceptance of the two requests.
If the display stays frozen, collect new evidence before changing drivers or disabling outputs.
Chezmoi installs the helper only on Hyprland desktops.

## Hardware acceptance test

Save your work before each sleep test.
Make sure that the lock screen appears before sleep and accepts your password after resume.
Record the kernel, Hyprland, Aquamarine, and NVIDIA versions with each result.

| Case | Expected result |
| --- | --- |
| Laptop only, lid open, timer suspend | Internal panel returns and unlock works |
| Laptop only, close then open lid | Internal panel returns and unlock works |
| Home ultrawide, close lid without sleep | Internal panel disables, ultrawide remains active |
| Work dock, open lid before connecting, then suspend/resume | All configured displays return and unlock works |
| Sleep docked, disconnect dock, resume | Internal panel returns |
| Personal desktop | Generic monitor rules work without laptop-specific commands |

If a case fails, record the exact case and collect these logs:

```sh
journalctl -b -k --since '10 minutes ago'
hyprctl version
hyprctl monitors all
hyprctl configerrors
```

Review logs for private content before sharing them.

`uv run tests/test_hypr_rescue.py` runs the helper against a stand-in `hyprctl`.
It covers instance selection, request errors, and timeouts.
It does not exercise display hardware, session locking, or suspend.
