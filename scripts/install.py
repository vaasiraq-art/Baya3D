#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Install Baya 3D using Blender's Python; never save startup or scene data."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib
import json
from pathlib import Path
import shutil
import sys
import uuid


REPO_ROOT = Path(__file__).resolve().parent.parent


def snapshot_targets(targets: dict[str, Path], backup: Path) -> dict:
    """Copy only named install targets into a new, private backup directory."""
    backup.mkdir(parents=True, exist_ok=False)
    manifest = {"format": 1, "targets": {}}
    for name, target in targets.items():
        target = target.resolve()
        existed = target.exists()
        entry = {"path": str(target), "existed": existed, "directory": target.is_dir()}
        manifest["targets"][name] = entry
        if existed:
            if target.is_dir():
                shutil.copytree(target, backup / name)
            else:
                shutil.copy2(target, backup / name)
    (backup / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def restore_targets(targets: dict[str, Path], backup: Path, manifest: dict) -> None:
    """Restore this process's known targets; never trust deletion paths from JSON."""
    expected_names = {"addon": "blender_maya", "preset": "Baya_3D.py", "preferences": "userpref.blend"}
    for name, target in targets.items():
        target = target.resolve()
        if target.name != expected_names[name] or target.parent == target:
            raise RuntimeError(f"Refusing unexpected rollback target: {target}")
        entry = manifest["targets"][name]
        if str(target) != entry["path"]:
            raise RuntimeError("The rollback target changed after backup")
        if target.is_dir():
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()
        if entry["existed"]:
            target.parent.mkdir(parents=True, exist_ok=True)
            if entry["directory"]:
                shutil.copytree(backup / name, target)
            else:
                shutil.copy2(backup / name, target)


def install(apply_theme: bool = False) -> Path:
    import addon_utils
    import bpy

    if bpy.app.version[:2] != (5, 3):
        raise RuntimeError("This experimental installer currently supports Blender 5.3 only")
    if not bpy.app.background:
        raise RuntimeError("Run this installer in a separate Blender --background process")

    source = (REPO_ROOT / "blender_maya").resolve()
    if not (source / "__init__.py").is_file():
        raise RuntimeError("Run install.py from a complete Baya3D checkout")

    scripts = Path(bpy.utils.user_resource("SCRIPTS", create=True)).resolve()
    config = Path(bpy.utils.user_resource("CONFIG", create=True)).resolve()
    targets = {
        "addon": scripts / "addons" / "blender_maya",
        "preset": scripts / "presets" / "keyconfig" / "Baya_3D.py",
        "preferences": config / "userpref.blend",
    }
    # Reject links escaping the selected resource directories before backing up
    # or entering rollback. A development checkout must never delete itself.
    for name, target in targets.items():
        allowed_root = config if name == "preferences" else scripts
        if target.is_symlink() or not target.resolve().is_relative_to(allowed_root):
            raise RuntimeError(f"Install target escapes the selected user resources: {target}")
    destination = targets["addon"].resolve()
    if source == destination or destination in source.parents:
        raise RuntimeError("The source checkout is inside the installed add-on; move it before installing")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    backup = config.parent / "baya3d-backups" / stamp
    manifest = snapshot_targets(targets, backup)
    print(f"Baya 3D backup: {backup}")

    try:
        if "blender_maya" in bpy.context.preferences.addons:
            addon_utils.disable("blender_maya", default_set=False)
        for name in tuple(sys.modules):
            if name == "blender_maya" or name.startswith("blender_maya."):
                del sys.modules[name]
        if destination.name != "blender_maya" or destination.parent != (scripts / "addons").resolve():
            raise RuntimeError("Unexpected add-on destination")
        if destination.exists():
            shutil.rmtree(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, destination, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"))
        for name in ("LICENSE", "THIRD_PARTY_NOTICES.md"):
            shutil.copy2(REPO_ROOT / name, destination / name)
        if str(destination.parent) not in sys.path:
            sys.path.insert(0, str(destination.parent))
        importlib.invalidate_caches()
        addon_utils.modules_refresh()
        module = addon_utils.enable("blender_maya", default_set=True, persistent=True)
        if module is None or "blender_maya" not in bpy.context.preferences.addons:
            raise RuntimeError("Baya 3D could not be enabled")
        module.controls.install_keyconfig()
        if apply_theme:
            module.ui.apply_theme()
        if bpy.context.window_manager.keyconfigs.active.name != "Baya_3D":
            raise RuntimeError("Baya key configuration did not activate")
        if "FINISHED" not in bpy.ops.wm.save_userpref():
            raise RuntimeError("Blender did not save preferences")
    except BaseException:
        restore_targets(targets, backup, manifest)
        print(f"Installation failed; restored the files backed up in {backup}", file=sys.stderr)
        raise

    print("Installed Baya 3D add-on and keymap. Restart Blender to use them.")
    print("No startup or scene file was saved.")
    return backup


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--theme", action="store_true", help="Also apply the optional charcoal theme")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    install(apply_theme=args.theme)


if __name__ == "__main__":
    main()
