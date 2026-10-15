# Shortcuts

These are the intended current mappings in the Baya key configuration. Use them with the pointer over the 3D viewport and no text field in edit mode. Mode-specific tools require a compatible active object. Other editors retain their own controls, and unmapped actions inherit Blender's Industry Compatible keymap.

| Key or gesture | Action |
| --- | --- |
| Alt + left/middle/right mouse drag | Orbit / pan / dolly |
| Q / W / E / R | Select / Move / Rotate / Scale tool |
| T | Universal transform manipulator (`builtin.transform`) |
| Y | Recall last modeling tool other than Select/Move/Rotate/Scale |
| G | Repeat last operation |
| F / A | Frame selected / frame all |
| Ctrl + D | Duplicate selected objects in place |
| Ctrl + Z / Ctrl + Y | Undo / redo |
| Ctrl + N / O / S | New / open / save |
| Ctrl + Shift + S | Save As |
| 1 / 2 / 3 | Base mesh / cage and smooth preview / smooth preview |
| Page Up / Page Down | Raise / lower visible smooth preview subdivisions |
| 4 / 5 / 6 / 7 | Wireframe / solid / material preview / rendered scene lighting |
| F8 | Toggle object and component mode |
| F9 / F10 / F11 | Vertex / edge / face component selection |
| F12 | UV Editing workspace |
| F2 / F3 / F4 / F5 / F6 | Modeling / rigging / animation / FX / rendering shelf |
| Right mouse | Selection marking pie |
| Shift + right mouse | Primitive creation pie |
| Tap Space | Single/four-view layout |
| Hold Space | Hotbox-style pie |
| S | Insert location, rotation and scale keys |
| Shift + W / E / R | Insert location / rotation / scale keys |
| Alt + V | Play/pause |
| Alt + comma / period | Previous/next frame |
| Comma / period | Previous/next keyframe |
| Hold K + middle mouse drag | Scrub animation |
| P / Shift + P | Parent / unparent |
| Ctrl + E in mesh component mode | Extrude |
| Ctrl + A | Toggle Channel Box and reveal native object attributes |
| Ctrl + Shift + A / I | Select all / invert selection |
| Tab | Search Blender commands |

T selects Blender's universal transform tool as an approximation of Show Manipulator. It cannot expose Maya node-specific manipulators. Y depends on a previously chosen modeling tool. Workspace-switch shortcuts require the matching workspace to exist in the current `.blend` file.

See [limitations](limitations.md) for snapping, pivot editing, hotbox release behavior, preview rendering and engine differences. Use the [testing checklist](testing.md) to report behavior that differs from this table.
