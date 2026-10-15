# Current limits

Baya 3D is a Blender add-on. It does not replace Blender's engine or implement Autodesk Maya itself. The project is experimental and has not completed a full mode-by-mode hotkey audit.

- Blender's coordinate system remains Z-up. Scene files remain `.blend`; MEL and Maya `.ma`/`.mb` support are not supplied.
- Modifiers and nodes provide Blender's equivalent of input history. Maya's dependency graph, construction history and Attribute Editor are not recreated.
- The Channel Box is a Blender sidebar panel; detailed attributes remain in Blender's native Properties editor.
- The hotbox uses Blender menus/pies. The complete Maya menu grid and exact held-Space release behavior are unfinished.
- Four-view uses Blender's quad-view layout. Existing workspaces and editor layouts influence the result.
- T/manipulator behavior is limited to the operators and gizmos available in Blender. Maya's node-specific manipulators are not available.
- Held X/C/V snapping and D pivot-edit gestures are unfinished. Blender's header controls remain available.
- Smooth preview uses dedicated Subdivision Surface and smooth-shading Geometry Nodes modifiers, preserving base geometry and existing modifiers. Preview rendering is disabled by default; enable the preview modifiers' render visibility intentionally if wanted.
- 6/7 display modes use Blender material preview/rendering. Arnold, Bifrost, nCloth and Maya-specific animation layers are not included.
- F12 requests the UV Editing workspace rather than a Maya in-viewport UV selection mask. Workspace switches require that workspace in the file.
- K scrubbing updates Blender's scene; Maya's held-pose scrub behavior is not replicated.
- The source installer adds the add-on/keymap and optionally the theme. It does not ship a saved startup scene or recreate a user's previous local layout.

See [ROADMAP.md](../ROADMAP.md) for planned improvements. Contributions should describe the exact action, compatible Blender equivalent and remaining differences.
