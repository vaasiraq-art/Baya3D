#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Build a deterministic legacy Blender add-on ZIP from source files only."""

from __future__ import annotations

import argparse
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parent.parent


def build(destination: Path | None = None) -> Path:
    destination = destination or ROOT / "dist" / "Baya3D-addon.zip"
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    files = [(path, "blender_maya/" + path.relative_to(ROOT / "blender_maya").as_posix())
             for path in sorted((ROOT / "blender_maya").rglob("*"))
             if path.is_file() and "__pycache__" not in path.parts and path.suffix in {".py", ".png", ".svg", ".ico"}]
    files += [(ROOT / name, "blender_maya/" + name) for name in ("LICENSE", "THIRD_PARTY_NOTICES.md")]
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for source, name in files:
            info = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, source.read_bytes())
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    print(build(parser.parse_args().output))
