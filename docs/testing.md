# Testing Baya 3D

## Automated checks

```sh
python -m compileall -q blender_maya scripts tests
python scripts/build_addon.py
blender --background --factory-startup --python tests/blender_smoke.py
```

The smoke test registers from the checkout, checks keymap operator properties, verifies core tool targets and tests that preview changes preserve the base mesh and existing modifiers. It unregisters afterward and never saves preferences or scenes.

An optional GitHub Actions template is included at `.github/workflow-templates/source-checks.yml.example`. A maintainer can copy it to `.github/workflows/checks.yml` to enable automated syntax and packaging checks. It does not download or execute a Blender build. The template is not enabled automatically.

## Interactive checklist

Use an isolated profile and a simple disposable scene. Record the full Blender build, OS and keyboard layout. Run these checks after a fresh launch and again after disable/re-enable:

1. With the pointer over the viewport, press Q/W/E/R individually. Confirm the toolbar selection and visible gizmo, then drag on a selected object and undo the change.
2. Repeat in mesh Edit Mode and Pose Mode. Verify transforms affect the selected components/bones and do not switch modes unexpectedly.
3. Press T with representative objects and tools; record the available manipulator and any differences from the documented approximation. Choose a modeling tool, press W, then Y and verify recall.
4. Test Alt + mouse orbit, pan and dolly, then F/A framing.
5. Test 1/2/3 smooth preview with an existing modifier stack. Verify 1 restores the visible base state and the original mesh remains unchanged. Check render visibility separately.
6. Test 4/5/6/7 display, F8-F12 components/workspaces, right-mouse pies, Ctrl+D duplicate and Ctrl+E extrude.
7. Tap Space, hold Space, cancel with Esc, and change focus during the gesture. Note release behavior.
8. Test S, Shift+W/E/R, Alt+V, key/frame stepping, K+MMB scrub and cancellation.
9. Put the pointer over Outliner, a text field, Timeline and another editor; confirm keys respect editor context and text entry.
10. Change the OS keyboard layout and test again if reporting layout-related input problems.
11. Switch away from the Baya keymap, disable the add-on and verify native menus/tool headers return. Restart and ensure the selected preferences persist.

Keep screenshots small and remove file paths, user names and project details before sharing. A minimal synthetic `.blend` reproducer is preferable to a production scene.
