# Hyprland display recovery

Hypridle locks the session before sleep and wakes the displays after resume.
It waits for the session lock with `inhibit_sleep = 3`.
It does not use a fixed delay as proof that the lock is ready.
The [Hypridle documentation](https://wiki.hypr.land/0.49.0/Hypr-Ecosystem/hypridle/) describes this behavior.

On laptops with a configured internal panel, closing the lid disables that panel.
Opening the lid while awake reloads the monitor configuration.
After resume, Hypridle reads the ACPI lid state and reloads the configuration if the lid is open.
This covers a lid-open event that was lost while the input devices were unavailable.
`/proc/acpi/button/lid/LID/state` is the verified path recorded for GAM-DEV001.
Other laptops use the same `/proc/acpi/button/lid/*/state` pattern.
Desktop machines do not get the lid bindings or the ACPI state check.

`allow_session_lock_restore` permits a replacement locker if the original locker crashes.
The recovery helper does not kill or restart the locker.

## Monitor portability

Monitor data lives in `.chezmoidata/hyprland.toml`.
The `internal_outputs` table selects the internal panel for known laptops.
Set local `data.hyprland.laptop_output` to override that selection on another laptop.
Known hardware uses the matching hostname entry.
Other machines use the preferred mode for each connected display.
Hardware names do not appear in recovery commands.

To override the layout on one machine, add this table to the local chezmoi configuration:

```toml
[[data.hyprland.monitors]]
output = ""
mode = "preferred"
position = "auto"
scale = 1
```

The initialization template preserves this override.
An empty array selects the shared defaults.
Chezmoi excludes the recovery helper on desktops other than Hyprland.

## Recover a display

`hypr-rescue` reloads the configured monitors and requests display power.
It preserves the lock screen and does not activate another login session.
It accepts a signature, the unique name of a running Hyprland instance.
The [hyprctl documentation](https://wiki.hypr.land/0.54.0/Configuring/Using-hyprctl/) describes instance selection and configuration reloads.

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

## GAM-DEV001 investigation

The September 11 and 12 session transcripts describe two different failures.
This summary records their final findings, not independent live verification.

A display controller assigns monitor signals to display pipelines.
The dock case showed a rejected assignment after resume, with frozen kernel text on some screens.
The later undocked case restored the display controller but left the internal panel disabled.
The investigation attributes the second case to a missed lid-open event while the input devices were unavailable.
Reading the ACPI lid state after resume removes the dependency on that missing input event.

The investigation first blamed `nvidia-sleep.sh` for the console switch, then withdrew that claim.
The observed boot lacked `/proc/driver/nvidia/suspend`, so the script exited before its console-switch command.
The final explanation attributes the switch to the loaded NVIDIA kernel modules.
Disabling the NVIDIA sleep services alone is not an established fix.

Disabling NVIDIA modules or framebuffer consoles was proposed, not tested.
Those changes affect GPU availability or text consoles and are not part of this configuration.
The dock failure still needs a controlled hardware test.
This PR does not establish that the kernel or compositor fault is fixed.

## Dock workflow

Open the lid before you connect the dock.
If the dock is connected while the laptop is asleep with the lid closed, the internal panel released its display pipe.
The compositor's restore after resume is then rejected.
This is an Aquamarine defect: restore does not read the kernel's connector routing.
This configuration does not fix it.
The [corrected investigation](https://github.com/PixelHabits/dotfiles/pull/5#issuecomment-5653825227) records the source references and incident results.
The disable-all loop did not repair either recorded incident and is not restored here.

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
Mock tests cover instance selection, request errors, and command boundaries.
They do not exercise display hardware, session locking, or suspend.
