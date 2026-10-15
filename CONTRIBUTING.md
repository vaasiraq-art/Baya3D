# Contributing to Baya 3D

Thank you for helping artists work comfortably in Blender. Contributions can be code, reproducible bug reports, usability feedback, tests, documentation or original design work.

## Before changing behavior

1. Search existing issues and check [ROADMAP.md](ROADMAP.md).
2. Describe the artist action being improved, the current behavior and the intended result.
3. For Maya parity work, cite a public Autodesk reference and explain the Blender equivalent. Document differences where the engines behave differently.

You do not need permission for a small fix. For changes affecting many keys or editors, open an issue first so contributors can agree on conflicts and scope.

## Development

Use a Blender 5.3 development build and a separate test preferences directory. The source package is `blender_maya`; existing operator identifiers use `maya_style.*` for compatibility. User-facing labels should say Baya 3D. Avoid renaming internal identifiers without a migration plan.

Run the syntax and Blender smoke checks documented in the README. Test registration, disabling, re-enabling and a fresh restart. For keyboard changes, complete the focused parts of [docs/testing.md](docs/testing.md). Include the tested build and results in the pull request.

Do not save a contributor's startup scene or preferences into the repository. Keep add-on registration free of preference/scene saves. Any installer must back up what it changes and make recovery possible. Preserve user geometry, modifiers and scene settings unless a specific operator explicitly changes them.

## Pull requests

- Keep the change focused and describe the visible before/after behavior.
- Explain mode/editor restrictions and any shortcut conflicts resolved.
- Include tests for lasting behavior or relevant manual steps and results.
- Update the shortcut guide and limits when behavior changes.
- Include only code and assets you can contribute under the project license. Do not upload Autodesk source, documentation, logos, private scenes, account information or engine binaries.

By contributing, you agree that your contributions may be distributed under GPL-3.0-or-later. Existing third-party notices must be preserved. No contributor license agreement is currently required.

Treat other contributors respectfully. Explain disagreements with examples and reproducible evidence. Report sensitive personal information accidentally committed to the repository privately to the repository owner instead of repeating it in a public issue.
