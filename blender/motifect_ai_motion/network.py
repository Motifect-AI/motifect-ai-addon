# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Motifect

"""Blender online-access guard for marketplace / extension guidelines."""

from __future__ import annotations


class OnlineAccessDisabledError(RuntimeError):
    """Raised when Blender's Allow Online Access preference is off."""


def ensure_online_access() -> None:
    import bpy

    if not getattr(bpy.app, "online_access", True):
        raise OnlineAccessDisabledError(
            "Internet access is disabled. Enable Edit → Preferences → System → "
            "Allow Online Access, then try again."
        )
