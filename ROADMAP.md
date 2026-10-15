# Roadmap

This is a direction for contributors, not a claim that the features below are complete.

## Priority 1: dependable everyday controls

- Audit physical Q/W/E/R/T events after cold startup, keymap reload and add-on re-enable.
- Test object, mesh, curve, armature, pose and editor contexts; resolve conflicting mode handlers.
- Preserve custom operator properties when presets load before operator registration.
- Expand automated keymap and data-preservation regressions, plus a repeatable interactive checklist.
- Define T manipulator behavior and Y/G history behavior precisely; document approximations.
- Add safe per-feature configuration and predictable disable/uninstall behavior.

## Priority 2: interaction and workspace parity

- A held-Space hotbox with clear press/release/cancel semantics.
- Context-sensitive marking menus and stable four-view transitions.
- More complete Channel Box/Attribute Editor switching and input history navigation.
- Held X/C/V snapping and D pivot-edit workflows, with mode-aware conflict handling.
- Portable optional workspace/theme presets and version migration.

## Priority 3: production workflows

- Rigging shelves for joint/armature creation, parenting, skinning and weight editing.
- Animation workflow reviews for keying, curve editing, playback, scrubbing and pose tools.
- UV and modeling tool parity grounded in Blender's available operators.
- Better material, rendering and FX entry points while preserving Blender terminology where needed.
- Accessibility, configurable visual density, localization and documentation examples.

## Release readiness

- Support a stable Blender release with a documented compatibility matrix.
- Package signed/checksummed artifacts where practical and publish reproducible build instructions.
- Expand platform testing beyond the original Windows setup.
- Review interoperability expectations: Maya scene formats, MEL, Arnold, Bifrost and nCloth are not supplied by this add-on. Separate integrations would require independent design and review.
