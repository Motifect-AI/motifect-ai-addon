# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Motifect

"""Safe register/unregister — clears stale RNA classes from failed installs."""

import bpy


def _unregister_stale(class_name: str) -> None:
    stale = getattr(bpy.types, class_name, None)
    if stale is None:
        return
    try:
        bpy.utils.unregister_class(stale)
    except RuntimeError:
        pass


def register_class(cls) -> None:
    _unregister_stale(cls.__name__)
    if getattr(cls, "is_registered", False):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass
    bpy.utils.register_class(cls)


def unregister_class(cls) -> None:
    if getattr(cls, "is_registered", False):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass
    _unregister_stale(cls.__name__)
