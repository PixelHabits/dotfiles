# Waybar

The bar uses the shared app catalog for workspace icons.
Laptop configurations include the battery and backlight modules.
Desktop configurations omit those modules.
The clock uses the machine timezone.

The media module shows playback information without a separate MPD module.
Keyboard input access and Sway-specific modules are not required.

Run `python3 tests/waybar.py` to render laptop and desktop configurations.
The test does not start Waybar or apply desktop files.
