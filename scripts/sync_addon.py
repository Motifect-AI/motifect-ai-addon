#!/usr/bin/env python3
"""Copy monorepo add-on source into this public repo layout and build zip."""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT.parent / "motifect_motion"
DST = ROOT / "motifect_ai_motion"
ZIP_PATH = ROOT / "motifect_ai_motion.zip"
PKG = "motifect_ai_motion"


def sync_tree() -> None:
    if not SRC.is_dir():
        raise SystemExit(f"Source not found: {SRC}")
    if DST.exists():
        shutil.rmtree(DST)
    shutil.copytree(
        SRC,
        DST,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    print(f"Synced {SRC} -> {DST}")


def build_zip() -> None:
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(DST.rglob("*")):
            if not path.is_file():
                continue
            if "__pycache__" in path.parts:
                continue
            arc = f"{PKG}/{path.relative_to(DST).as_posix()}"
            zf.write(path, arc)
    print(f"Built {ZIP_PATH}")


if __name__ == "__main__":
    sync_tree()
    build_zip()
