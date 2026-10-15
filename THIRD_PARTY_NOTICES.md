# Third-party notices

## Blender and the Industry Compatible keymap

Baya 3D imports the Industry Compatible keymap from the user's installed Blender at runtime and adapts its generated keymap data. That Blender source file declares:

```text
SPDX-FileCopyrightText: 2019-2023 Blender Authors
SPDX-License-Identifier: GPL-2.0-or-later
```

The file is normally located at `scripts/presets/keyconfig/keymap_data/industry_compatible_data.py` inside Blender's versioned resource directory. It is **not copied into this source repository**. A generated installed Baya key preset contains adapted data derived from that component; preserve this attribution if distributing such presets. Baya 3D distributes its own code under GPL-3.0-or-later and retains the upstream component's original GPL-2.0-or-later notice. Blender's own distribution contains its corresponding license and notices.

- Upstream project: <https://www.blender.org/>
- Upstream source: <https://projects.blender.org/blender/blender>
- GPL version 3 text: <https://www.gnu.org/licenses/gpl-3.0.txt>
- GPL version 2 text: <https://www.gnu.org/licenses/old-licenses/gpl-2.0.txt>

Baya 3D uses Blender's public Python API and built-in UI/operator definitions. Blender engine binaries and their additional dependencies are not included here. Their licenses and notices remain part of the separately installed Blender distribution.

## Original Baya assets and launcher

The Baya icon artwork, icon-generation script, launcher source and add-on source in this repository are supplied under the project's GPL-3.0-or-later license, unless a file explicitly states otherwise. The Windows launcher uses Microsoft .NET Framework APIs; the framework is not bundled here.

## Autodesk references

Maya workflow names and shortcut conventions are used as functional reference points. Autodesk software, manuals, logos and proprietary assets are not distributed with Baya 3D. Baya 3D is not affiliated with or endorsed by Autodesk. Autodesk and Maya names remain the trademarks of their respective owners.
