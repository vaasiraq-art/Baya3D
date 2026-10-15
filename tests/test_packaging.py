# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parent.parent


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PackagingTests(unittest.TestCase):
    def test_archive_is_reproducible_and_contains_only_distributable_files(self):
        builder = load_script("build_addon")
        with tempfile.TemporaryDirectory() as temp:
            first = builder.build(Path(temp) / "first.zip")
            second = builder.build(Path(temp) / "second.zip")
            self.assertEqual(first.read_bytes(), second.read_bytes())
            with zipfile.ZipFile(first) as archive:
                names = set(archive.namelist())
                required = {"blender_maya/" + name for name in (
                    "__init__.py", "controls.py", "ui.py", "branding.py", "assets/Baya3D.png",
                    "LICENSE", "THIRD_PARTY_NOTICES.md")}
                self.assertTrue(required.issubset(names))
                for name in names:
                    self.assertTrue(name.startswith("blender_maya/"))
                    self.assertNotIn("..", Path(name).parts)
                    self.assertNotIn("__pycache__", name)
                    self.assertNotIn(Path(name).suffix, {".exe", ".dll", ".pdf", ".blend", ".log", ".pyc"})
                for source in (ROOT / "blender_maya").glob("*.py"):
                    self.assertEqual(archive.read("blender_maya/" + source.name), source.read_bytes())

    def test_installer_rollback_restores_existing_files_and_removes_new_targets(self):
        installer = load_script("install")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            targets = {"addon": root / "addons" / "blender_maya",
                       "preset": root / "presets" / "Baya_3D.py",
                       "preferences": root / "config" / "userpref.blend"}
            targets["addon"].mkdir(parents=True)
            (targets["addon"] / "old.py").write_text("original addon", encoding="utf-8")
            targets["preferences"].parent.mkdir(parents=True)
            targets["preferences"].write_bytes(b"original preferences")
            backup = root / "backup"
            manifest = installer.snapshot_targets(targets, backup)
            (targets["addon"] / "new.py").write_text("new addon", encoding="utf-8")
            targets["preferences"].write_bytes(b"changed preferences")
            targets["preset"].parent.mkdir(parents=True)
            targets["preset"].write_text("new preset", encoding="utf-8")
            installer.restore_targets(targets, backup, manifest)
            self.assertEqual(targets["preferences"].read_bytes(), b"original preferences")
            self.assertEqual((targets["addon"] / "old.py").read_text(), "original addon")
            self.assertFalse((targets["addon"] / "new.py").exists())
            self.assertFalse(targets["preset"].exists())


if __name__ == "__main__":
    unittest.main()
