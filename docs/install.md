# Installation and recovery

## Supported setup

The current experimental target is Blender **5.3**. Testing began with a 5.3.0 Beta build. The installer refuses other Blender minor versions because the UI and keymap APIs have not been validated for them. A beta update can still introduce changes; include the complete build string in bug reports.

Run the installer using the Blender executable you want to configure. It operates on that process's user-resource directories, including any resource-directory environment overrides. It does not search or modify other Blender versions.

```powershell
.\scripts\install.ps1 -BlenderExe "C:\path\to\Blender\blender.exe"
.\scripts\install.ps1 -BlenderExe "C:\path\to\Blender\blender.exe" -Theme
```

Or run `blender --background --python scripts/install.py`, with optional `-- --theme`. Do not add `--factory-startup` for normal installation: it would start from factory preferences instead of preserving your existing preferences.

## Changes made

The installer creates a backup, copies `blender_maya` into the user add-on directory, enables it, installs and selects the `Baya_3D` key configuration, and saves preferences. `--theme` also applies the charcoal theme. It does not create a new workspace layout, change scene units/frame rates, save a project, or replace the startup scene. Shelves appear in an existing 3D viewport tool header and the Channel Box is in the sidebar's Baya tab.

Backups are created under the selected Blender profile's `baya3d-backups` folder. The installer prints its exact location and writes a `manifest.json` containing the previous add-on, key preset and `userpref.blend` locations and whether each existed. Installation failures attempt to restore those backed-up files before exiting with an error.

Close other Blender windows using the same preferences before installing so an older process cannot overwrite the result when it exits. Relaunch the selected Blender version after the installer succeeds.

## Recovery

Close Blender. Read the latest backup's `manifest.json`. For each recorded target, copy the corresponding backup over the target if `existed` is true. If `existed` is false, remove only the newly installed target named in that entry. The three possible targets are the `blender_maya` add-on directory, the `Baya_3D.py` preset, and `config/userpref.blend`. Do not delete the full Blender profile.

For temporary use without restoring the complete preferences backup, first select another keymap in Preferences, then disable Baya 3D and save preferences. If you applied the theme, choose a different theme or restore the preferences backup. Existing startup layouts and scene files are not part of installation or recovery.

## Manual installation

Run `python scripts/build_addon.py` to create `dist/Baya3D-addon.zip`. Install that legacy add-on ZIP through Blender Preferences' install-from-disk action, then enable Baya 3D. This enables its UI only; the keymap is deliberately opt-in.

To activate the keymap from Blender's Python Console after enabling:

```python
from blender_maya import controls
controls.install_keyconfig()
# Save preferences through Blender's Preferences UI when you want it persistent.
```

The theme is separately available through `from blender_maya import ui; ui.apply_theme()`. Disabling the add-on requires switching to another keymap first so custom operators are no longer referenced.

## Development isolation

Use an isolated preferences directory before interactive tests. For example, set `BLENDER_USER_CONFIG` and `BLENDER_USER_SCRIPTS` to temporary directories in the shell used to launch Blender. Leave your personal project files outside the test profile. The smoke tests use factory startup and only change in-memory state.
