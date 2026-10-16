<p align="center"><img src="branding/Baya3D.png" width="128" alt="Baya 3D logo"></p>

# Baya 3D

**An open-source, Maya-inspired workspace, UI, coordinate system and keyboard workflow for Blender.**

Baya 3D brings familiar Maya-style navigation, Menu Sets, Status Line, Tabbed Shelves, a Channel Box (with **Maya Y-Up `XYZ`** coordinate display and editing), Modeling Toolkit, Attribute Editor, context-sensitive Marking Menus, Viewport Heads-Up Display (HUD), MEL/Python Command Bar, and `1/2/3` Smooth Mesh Preview to Blender 5.3.

**Status: experimental (v2.0).** Development targets **Blender 5.3.0 Beta**. This repository contains a 100% clean-room `GPL-3.0-or-later` add-on and optional Windows launcher source; install Blender separately.

## What you can try

- **Top Menu Bar with Menu Sets (`F2`–`F6`)**: Switch between *Modeling*, *Rigging*, *Animation*, *FX*, and *Rendering* menu sets (`Mesh`, `Edit Mesh`, `Mesh Tools`, `Mesh Display`, `Curves`, `Surfaces`, `Deform`, `UV`, `Skeleton`, `Skin`, `Constrain`, `Key`, `Playback`, `FX / Dynamics`, `Lighting/Shading`, `Render`).
- **Status Line & 8 Tabbed Shelves**: Selection masks (`Object F8`, `Vertex F9`, `Edge F10`, `Face F11`, `Multi`, `UV F12`), snapping toggles (`Grid X`, `Curve/Edge C`, `Vertex V`, `Edit Pivot D`, `Soft Select B`, `Symmetry X`), history/transform icons (`Center Pivot`, `Delete History`, `Freeze Transformations`), and shelves for *Curves*, *Polygons*, *Sculpting*, *UV Editing*, *Rigging*, *Animation*, *Rendering*, and *FX*.
- **Right Dock (`Ctrl + A`)**: Switch between **Channel Box / Display Layers**, **Modeling Toolkit**, and **Attribute Editor** (`Transform`, `Shape`, `Shader` with one-click *Standard Surface / Lambert / Blinn / Phong / Surface Shader* presets, and `Render`).
- **Maya Y-Up `XYZ` Coordinate System**: View and edit `Translate X/Y/Z`, `Rotate X/Y/Z`, and `Scale X/Y/Z` in Maya's `Y-Up` convention (`Y` = height, `Z` = depth) or toggle to native `Blender Z-Up` at any time.
- **Navigation, Snapping & Pivot Editing**: `Alt + LMB/MMB/RMB` camera navigation, `Q/W/E/R/T` tools, held `X / C / V` snapping (Grid / Curve-Edge / Vertex), `D` / `Insert` Pivot Edit mode, `B` Soft Selection, and `1/2/3` non-destructive Smooth Mesh Preview.
- **Context-Sensitive Marking Menus & Hotbox**: `RMB` Component/Object Marking Menu, `Shift + RMB` context-aware Polygon Tool Marking Menu, `Ctrl + RMB` Selection Conversion Menu, and `Space` (tap for Four-View, hold for Hotbox).
- **Viewport HUD & Bottom Command Bar**: Live Poly Count (`Verts`, `Edges`, `Faces`, `Tris`, `UVs`), Object Details, active Snap/Pivot banners, camera & axis HUD, plus a bottom **MEL / Python Command Line** and Time/Range controls.

See the [shortcut guide](docs/shortcuts.md), [known limits](docs/limitations.md) and [roadmap](ROADMAP.md). Exact Maya behavior is a development goal, not a current compatibility guarantee. Blender's engine, data model and `.blend` file format remain in use.

## Install

Save your work and close other Blender windows using the same preferences before installing. The installer updates the current Blender version's add-on, keymap and preferences. It creates a timestamped backup first. It does **not** save or replace `startup.blend` or a scene file.

From a cloned checkout on Windows:

```powershell
.\scripts\install.ps1 -BlenderExe "C:\path\to\Blender\blender.exe" -Theme
```

The script can also find `BLENDER_EXE`, `blender` on `PATH`, or a Blender executable beside the repository. Use `-Theme` to apply the charcoal Maya-style theme.

On other platforms, run Blender's bundled Python installer directly:

```sh
blender --background --python scripts/install.py
# Optional charcoal theme:
blender --background --python scripts/install.py -- --theme
```

Restart Blender after installation. Viewport keys work when the pointer is over the 3D viewport and a text field is not being edited. The add-on lives under its existing module name, `blender_maya`; its displayed name is **Baya 3D**.

See [installation and recovery](docs/install.md) for exact behavior, manual enablement, development and backups. The optional [Windows launcher](branding/README.md) can be built from source; no engine binaries are distributed here.

## Development checks

```sh
python -m compileall -q blender_maya scripts tests
python scripts/build_addon.py
python -m unittest discover -s tests -p "test_*.py" -v
blender --background --factory-startup --python tests/blender_smoke.py
```

The first three checks require only Python. The Blender smoke test runs in memory and does not save preferences or scenes. Interactive mouse/keyboard behavior still needs the [manual test checklist](docs/testing.md).

## License and attribution

Project code and original Baya artwork are available under **GPL-3.0-or-later**, unless a file says otherwise. See [LICENSE](LICENSE) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). The keymap uses Blender's installed Industry Compatible keymap at runtime; it is not bundled in this repository.

Baya 3D is an independent community project. It is not affiliated with, sponsored by, or endorsed by Autodesk or the Blender Foundation. Autodesk and Maya are trademarks of their respective owners. No Autodesk software, manuals or branding assets are included.
