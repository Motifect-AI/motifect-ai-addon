#!/usr/bin/env python3
"""Build a Fab-ready zip: MotifectMotion.uplugin at archive root."""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "unreal" / "MotifectMotion"
OUT = ROOT / "unreal" / "MotifectMotion_fab.zip"

SKIP_DIRS = {"__pycache__", "Intermediate", "Saved", "Binaries", ".git"}
SKIP_SUFFIXES = {".pyc", ".pyo"}


def build_fab_zip() -> None:
    if not SRC.is_dir():
        raise SystemExit(f"Plugin folder missing: {SRC}")
    if OUT.exists():
        OUT.unlink()
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(SRC.rglob("*")):
            if not path.is_file():
                continue
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            if path.suffix in SKIP_SUFFIXES:
                continue
            arc = path.relative_to(SRC).as_posix()
            zf.write(path, arc)
    print(f"Built {OUT}")


if __name__ == "__main__":
    build_fab_zip()
