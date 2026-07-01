bl_info = {
    "name": "Motifect Motion",
    "author": "Motifect",
    "version": (2, 2, 1),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar (N) > Motifect",
    "description": "Text-to-motion via motifect.io (account, API key & credits required)",
    "doc_url": "https://motifect.io/en/docs",
    "tracker_url": "https://github.com/Motifect-AI/motifect-ai-addon/issues",
    "category": "Animation",
}

import bpy

from . import operators, panels, preferences, properties
from .version import ADDON_VERSION


def register():
    try:
        unregister()
    except Exception:
        pass
    preferences.register()
    properties.register()
    operators.register()
    panels.register()
    print(f"[Motifect] Motifect Motion add-on registered (v{ADDON_VERSION})")


def unregister():
    panels.unregister()
    operators.unregister()
    properties.unregister()
    preferences.unregister()
