#!/usr/bin/env python3
"""Sync all DCC add-on sources into this public repo (single repo, per-platform folders)."""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADDONS = ROOT.parent.parent

SOURCES = (
    (ADDONS / "blender" / "motifect_motion", ROOT / "blender" / "motifect_ai_motion"),
    (ADDONS / "unreal" / "MotifectMotion", ROOT / "unreal" / "MotifectMotion"),
    (ADDONS / "unity" / "MotifectMotion", ROOT / "unity" / "MotifectMotion"),
)

IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", "Library", "Temp", "obj", "bin")
BLENDER_ZIP = ROOT / "blender" / "motifect_ai_motion.zip"
BLENDER_PKG = "motifect_ai_motion"
BLENDER_GPL = ADDONS / "blender" / "motifect_motion" / "LICENSE"
BLENDER_COPYING = ADDONS / "blender" / "motifect_motion" / "COPYING"


def sync_tree(src: Path, dst: Path) -> None:
    if not src.is_dir():
        raise SystemExit(f"Source not found: {src}")
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=IGNORE)
    print(f"Synced {src} -> {dst}")


def build_blender_zip() -> None:
    dst = ROOT / "blender" / "motifect_ai_motion"
    if not dst.is_dir():
        raise SystemExit(f"Blender add-on folder missing: {dst}")
    BLENDER_ZIP.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(BLENDER_ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(dst.rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            arc = f"{BLENDER_PKG}/{path.relative_to(dst).as_posix()}"
            zf.write(path, arc)
    print(f"Built {BLENDER_ZIP}")


def main() -> None:
    for src, dst in SOURCES:
        sync_tree(src, dst)
    # GPL license lives in dev source; ensure public blender folder has it
    if BLENDER_GPL.is_file():
        shutil.copy2(BLENDER_GPL, ROOT / "blender" / "LICENSE")
    if BLENDER_COPYING.is_file():
        dst_copying = ROOT / "blender" / "motifect_ai_motion" / "COPYING"
        shutil.copy2(BLENDER_COPYING, dst_copying)
    build_blender_zip()
    print("Run scripts/build_fab_zip.py for Unreal Fab archive.")


if __name__ == "__main__":
    main()
