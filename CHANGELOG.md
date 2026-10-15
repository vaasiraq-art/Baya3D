# Changelog

## Unreleased

- Published the Baya 3D source, original branding, GPL-3.0-or-later license, install scripts and contributor roadmap.
- Fixed Q/W/E/R/T after cold startup by using native tool bindings with cycling disabled.
- Added a guarded repair after add-on registration and file loads for custom shortcut properties lost during preset initialization.
- Preserve intentional keymap switching and later user customizations when no repair is needed.
- Added a regression that loads the preset before the add-on and checks the effective user keymaps after repair.
- Verified physical Q/W/E/R/T input in a running Blender 5.3.0 Beta session without modifying the selected model.
