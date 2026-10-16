# Roadmap

This is a direction for contributors and tracks what has landed in **Baya 3D v2.0** alongside upcoming work.

## Completed in v2.0

- **Top Menu Bar with Menu Sets (`F2`–`F6`)**: Dynamic switching between *Modeling*, *Rigging*, *Animation*, *FX*, and *Rendering* menu sets.
- **Status Line & 8 Tabbed Shelves**: Selection masks (`Obj`, `Vertex`, `Edge`, `Face`, `Multi`, `UV`), snapping toggles (`X` Grid, `C` Curve/Edge, `V` Vertex, `D` Pivot, `B` Soft Select, `Symmetry`), history/transform buttons, and 8 shelves (*Curves*, *Polygons*, *Sculpting*, *UV Editing*, *Rigging*, *Animation*, *Rendering*, *FX*).
- **Maya Y-Up `XYZ` Coordinate Mode**: Live `Y-Up` (`Translate/Rotate/Scale X, Y, Z`) display and editing in the Channel Box with one-click switching between `Maya Y-Up (XYZ)` and `Blender Z-Up (XYZ)`.
- **Right Dock Switcher (`Ctrl + A`)**: Integrated **Channel Box / Display Layers**, **Modeling Toolkit (`MTK`)**, and **Attribute Editor (`AE`)** with shader presets (*Standard Surface*, *Lambert*, *Blinn*, *Phong*, *Surface Shader*).
- **Context-Sensitive Marking Menus & Held Hotbox**: `RMB` Component/Object Marking Menu, `Shift + RMB` context-aware Polygon Tool Marking Menu, `Ctrl + RMB` Selection Conversion Menu, held-`Space` Hotbox with re-entry guard, held `X/C/V` snapping, and `D`/`Insert` Pivot Edit mode.
- **Viewport Heads-Up Display (`HUD`) & MEL/Python Command Bar**: Live Poly Count, Object Details, active Snap/Pivot banners, camera & axis indicator, and a bottom MEL/Python command bar + playback controls.

## Next Priorities

- Expand interactive modal options for polygon tools (live in-view option popups for Extrude, Bevel, and Multi-Cut).
- Deeper UV Editor shelf and marking-menu integration inside the 2D UV Editor space.
- Custom user-editable Shelf tab (`Custom`) for pinning any operator from the UI.
- Support upcoming stable Blender 5.x releases with a documented compatibility matrix and cross-platform CI checks.
