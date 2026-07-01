import bpy
from bpy.props import BoolProperty, StringProperty
from bpy.types import AddonPreferences

from .version import ADDON_VERSION


class MotifectPreferences(AddonPreferences):
    bl_idname = __package__

    api_key: StringProperty(
        name="API Key",
        description="Your Motifect API key from motifect.io (starts with mk_live_)",
        subtype="PASSWORD",
        default="",
    )
    api_base_url: StringProperty(
        name="API Base URL",
        description="Override only for development",
        default="https://api.motifect.io/api/v1",
    )
    show_setup_help: BoolProperty(
        name="Show Account Setup",
        default=True,
    )

    def draw(self, context):
        layout = self.layout
        layout.label(text=f"Add-on version: {ADDON_VERSION}")

        if self.show_setup_help:
            box = layout.box()
            box.label(text="Motifect account required", icon="INFO")
            col = box.column(align=True)
            col.scale_y = 0.9
            col.label(text="1. Sign up at motifect.io")
            col.label(text="2. Developer → API Keys → create key")
            col.label(text="3. Add credits (each generation uses credits)")
            col.label(text="4. Paste your mk_live_... key below")
            row = box.row()
            row.prop(self, "show_setup_help", text="Hide this help", toggle=True, icon="DISCLOSURE_TRI_DOWN")

        layout.separator()
        layout.prop(self, "api_key")
        layout.separator()
        row = layout.row(align=True)
        op = row.operator("wm.url_open", text="motifect.io", icon="URL")
        op.url = "https://motifect.io"
        op = row.operator("wm.url_open", text="API Docs", icon="URL")
        op.url = "https://motifect.io/en/docs"
        layout.prop(self, "api_base_url")


def register():
    from .registration import register_class

    register_class(MotifectPreferences)


def unregister():
    from .registration import unregister_class

    unregister_class(MotifectPreferences)


def get_preferences(context=None) -> MotifectPreferences:
    ctx = context or bpy.context
    addon = ctx.preferences.addons.get(__package__)
    if addon is None:
        raise RuntimeError("Motifect Motion addon preferences not found")
    return addon.preferences
