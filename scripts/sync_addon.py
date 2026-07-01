#!/usr/bin/env python3
"""Backward-compatible entry point — syncs all platforms."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sync_all import main

if __name__ == "__main__":
    main()
