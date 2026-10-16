# Current Limits & Engine Differences

Baya 3D is a clean-room Blender add-on (`GPL-3.0-or-later`). It provides a comprehensive Maya-inspired UI, coordinate view, and keyboard/mouse workflow on top of Blender 5.3, while using Blender's native geometry, modifier, animation, and rendering engines under the hood.

- **Coordinate System (`Maya Y-Up` vs `Blender Z-Up`)**: The Baya Channel Box and Viewport HUD default to **Maya Y-Up (`XYZ`)** (mapping `Y` to height and `Z` to depth for `Translate`, `Rotate`, and `Scale`) and allow switching to **Blender Z-Up (`XYZ`)** at any time. Internally, Blender's viewport world grid and `.blend` data model remain Z-up.
- **Scene Formats & MEL**: Scene files remain native `.blend` (with FBX/OBJ/USD/Alembic import/export via `File`). The bottom Command Bar executes common MEL command aliases (`polyCube`, `polySphere`, `CenterPivot`, `DeleteHistory`, `FreezeTransformations`, `CombinePolygons`, `select -all`, etc.) and `bpy.ops.*` expressions, rather than a full Maya MEL interpreter or `.ma`/`.mb` binary parser.
- **Construction History (`INPUTS`)**: Modifiers and Geometry Nodes provide Blender's equivalent of construction history. Clicking **Delete History** bakes active construction modifiers into the mesh while preserving your non-destructive `1/2/3` Smooth Mesh Preview modifiers.
- **Attribute Editor & Shaders**: The Baya Attribute Editor (`AE`) provides node tabs (`Transform`, `Shape`, `Shader`, `Render`) and one-click Maya shader presets (*Standard Surface*, *Lambert*, *Blinn*, *Phong*, *Surface Shader*) built on Blender's Principled BSDF node tree.
- **Smooth Mesh Preview (`1 / 2 / 3`)**: Uses dedicated Subdivision Surface and smooth-shading Geometry Nodes modifiers, preserving base geometry and existing artist modifiers. Render visibility on preview modifiers is off by default so base-mesh renders stay predictable unless explicitly enabled.

See [ROADMAP.md](../ROADMAP.md) for upcoming enhancements.
