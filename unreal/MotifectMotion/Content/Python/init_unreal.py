"""Motifect Motion — Unreal Editor startup hook."""

import unreal

try:
    import motifect_tools

    motifect_tools.register()
    unreal.log("[Motifect] Plugin loaded")
except Exception as exc:
    unreal.log_error(f"[Motifect] Failed to load: {exc}")
