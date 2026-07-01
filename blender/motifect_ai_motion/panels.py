# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Motifect

import bpy
from bpy.types import Panel

from .motifect_client import MODEL_CREDITS
from .version import RETARGET_ENABLED


class MOTIFECT_PT_main(Panel):
    bl_label = "Motifect Motion"
    bl_idname = "MOTIFECT_PT_main"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Motifect"

    def draw(self, context):
        layout = self.layout
        props = context.scene.motifect

        box = layout.box()
        box.label(text="Powered by motifect.io", icon="WORLD")
        col = box.column(align=True)
        col.scale_y = 0.85
        col.label(text="Requires a free account, API key & credits.")
        col.label(text="Set API key: Edit → Preferences → Add-ons → Motifect Motion")

        layout.separator()

        row = layout.row(align=True)
        if props.credit_balance >= 0:
            row.label(text=f"Credits: {props.credit_balance:,}")
        else:
            row.label(text="Credits: —")
        row.operator("motifect.refresh_credits", text="", icon="FILE_REFRESH")

        layout.separator()
        layout.prop(props, "prompt")
        layout.prop(props, "duration_seconds")
        layout.prop(props, "model_key")

        model_cost = MODEL_CREDITS.get(props.model_key)
        if model_cost is not None:
            layout.label(text=f"Uses {model_cost} credits per generation")

        layout.separator()

        if props.is_busy:
            box = layout.box()
            box.label(text="Generating motion…", icon="TIME")
            box.prop(props, "loading_progress_pct", slider=True, text=f"{props.loading_progress_pct}%")
            status = props.loading_status or props.status_message
            if status:
                box.label(text=status)
            if props.loading_elapsed_text:
                box.label(text=f"Elapsed {props.loading_elapsed_text}")
        else:
            col = layout.column(align=True)
            col.scale_y = 1.4
            col.operator("motifect.generate_motion", icon="PLAY")
            if props.status_message and props.status_message != "Ready":
                layout.label(text=props.status_message)

        layout.separator()
        layout.operator("motifect.open_docs", icon="URL")


class MOTIFECT_PT_retarget(Panel):
    bl_label = "Retarget"
    bl_idname = "MOTIFECT_PT_retarget"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Motifect"
    bl_parent_id = "MOTIFECT_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, _context):
        return not RETARGET_ENABLED

    def draw(self, _context):
        layout = self.layout
        box = layout.box()
        box.label(text="Coming soon", icon="LOCKED")
        box.label(text="Character retargeting is in development.")
        box.label(text="Use motifect.io retarget for now.")


classes = (
    MOTIFECT_PT_main,
    MOTIFECT_PT_retarget,
)


def register():
    from .registration import register_class

    for cls in classes:
        register_class(cls)


def unregister():
    from .registration import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)
