# Hyprland display recovery

Hypridle locks the session before sleep and wakes the displays after resume.
It waits for the session lock with `inhibit_sleep = 3`.
It does not use a fixed delay as proof that the lock is ready.
The [Hypridle documentation](https://wiki.hypr.land/0.49.0/Hypr-Ecosystem/hypridle/) describes this behavior.

The configuration does not disable the laptop panel when the lid closes.
A missed lid-open event can otherwise leave that panel disabled after resume.
Waking a display does not enable a disabled monitor.
With a dock connected, the laptop panel remains configured even when the lid is closed.
System power policy still controls whether closing the lid suspends the machine.

## Monitor portability

Monitor data lives in `.chezmoidata/hyprland.toml`.
Known hardware uses the matching hostname entry.
Other machines use the preferred mode for each connected display.
Hardware names do not appear in recovery commands.

To override the layout on one machine, add this table to the local chezmoi configuration:

```toml
[data.hyprland]
monitors = [", preferred, auto, 1"]
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
The helper does not claim success beyond acceptance of the two requests.
If the display stays frozen, collect new evidence before changing drivers or disabling outputs.

## GAM-DEV001 investigation

The September 11 and 12 session transcripts describe two different failures.
This summary records their final findings, not independent live verification.

A display controller assigns monitor signals to display pipelines.
The dock case showed a rejected assignment after resume, with frozen kernel text on some screens.
The later undocked case restored the display controller but left the internal panel disabled.
The investigation attributes the second case to a missed lid-open event while the input devices were unavailable.
Removing the lid bindings removes that configuration dependency.

The investigation first blamed `nvidia-sleep.sh` for the console switch, then withdrew that claim.
The observed boot lacked `/proc/driver/nvidia/suspend`, so the script exited before its console-switch command.
The final explanation attributes the switch to the loaded NVIDIA kernel modules.
Disabling the NVIDIA sleep services alone is not an established fix.

Disabling NVIDIA modules or framebuffer consoles was proposed, not tested.
Those changes affect GPU availability or text consoles and are not part of this configuration.
The dock failure still needs a controlled hardware test.
This PR does not establish that the kernel or compositor fault is fixed.

## Hardware acceptance test

Save your work before each sleep test.
Make sure that the lock screen appears before sleep and accepts your password after resume.
Record the kernel, Hyprland, Aquamarine, and NVIDIA versions with each result.

| Case | Expected result |
| --- | --- |
| Laptop only, close then open lid | Internal panel returns and unlock works |
| Sleep undocked, connect dock, resume | All configured displays return |
| Sleep docked, disconnect dock, resume | Internal panel returns |
| Docked, close lid without sleep | No monitor-disable command runs |
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
