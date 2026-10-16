# Testing Baya 3D

## Automated checks

```sh
python -m compileall -q blender_maya scripts tests
python scripts/build_addon.py
python -m unittest discover -s tests -p "test_*.py" -v
blender --background --factory-startup --python tests/blender_smoke.py
```

The smoke test registers from the checkout, verifies pre-registration keyconfig repair, checks `Q/W/E/R/T` native tool bindings across modes, verifies `1/2/3` smooth preview base-mesh and modifier preservation, and exercises the full Baya 3D v2.0 workflow:
- Maya `Y-Up (XYZ)` coordinate mapping (`maya_tx`, `maya_ty`, `maya_tz`, `maya_sx`, `maya_sy`, `maya_sz`)
- Freeze Transformations, Reset Transformations, and Center Pivot
- Component selection masks (`VERT`, `EDGE`, `FACE`, `MULTI`, `OBJECT`)
- Duplicate, Combine, and Delete Construction History
- Pivot Edit mode (`D` / `Insert`) and Snap toggles (`X` / `C` / `V`)
- Shader preset assignment (*Standard Surface*, *Lambert*, *Blinn*, *Phong*, *Surface Shader*) and Display Layer creation
- Shelf / Menu Set switching and MEL Command Line execution.

## Interactive checklist

1. Launch `Baya 3D.exe` (or `blender.exe`). Confirm the Topbar Menu Set selector, Status Line, Tabbed Shelf, Viewport HUD, Right Dock (`Baya` tab), and Bottom MEL/Python Command Bar are visible.
2. With the pointer over the viewport, press `Q/W/E/R` individually and drag the transform gizmo.
3. In the **Channel Box**, edit `Translate Y` in `Maya Y-Up (XYZ)` mode and confirm the object moves vertically; toggle `Blender Z-Up (XYZ)` to compare.
4. Test `Alt + LMB / MMB / RMB` orbit, pan and dolly, then `F` / `A` framing.
5. Test `1 / 2 / 3` smooth preview (`Page Up` / `Page Down` for divisions) and `4 / 5 / 6 / 7` viewport shading modes.
6. Test `RMB` (Component Marking Menu), `Shift + RMB` (Context Polygon Tool Marking Menu in Object, Vertex, Edge, and Face modes), and `Ctrl + RMB` (Selection Conversion Menu).
7. Hold `X` (Grid Snap), `C` (Curve/Edge Snap), and `V` (Vertex Snap) while moving an object; release to confirm snap state restores.
8. Press `D` (or `Insert`) to toggle Edit Pivot Mode, move the pivot, and press `D` again to exit.
9. Tap `Space` for Four-View quad layout; hold `Space` for the Hotbox.
10. Type `polySphere` or `FreezeTransformations` in the bottom MEL Command Bar and click Execute (`▶`).
