# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Motifect

import bpy
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)
from bpy.types import PropertyGroup

from .motifect_client import MODEL_CHOICES


def _poll_armature(_self, obj):
    return obj is not None and obj.type == "ARMATURE"


class MotifectRetargetSlot(PropertyGroup):
    slot_id: StringProperty(name="Slot")
    label: StringProperty(name="Label")
    required: BoolProperty(name="Required", default=False)
    source_bone: StringProperty(
        name="Source Bone",
        description="Bone on the Motifect source armature",
        default="",
    )
    target_bone: StringProperty(
        name="Target Bone",
        description="Bone on your character armature",
        default="",
    )


class MotifectProperties(PropertyGroup):
    prompt: StringProperty(
        name="Prompt",
        description="Describe the motion in English (10–180 characters)",
        default="A person turns sharply, regains balance, and continues walking.",
        maxlen=180,
    )
    duration_seconds: IntProperty(
        name="Duration (sec)",
        default=8,
        min=2,
        max=10,
    )
    model_key: EnumProperty(
        name="Model",
        items=[(key, label, "") for key, label in MODEL_CHOICES],
        default="motifect-v3",
    )

    source_armature: PointerProperty(
        name="Source",
        description="Motifect motion armature (auto-set after import)",
        type=bpy.types.Object,
        poll=_poll_armature,
    )
    target_armature: PointerProperty(
        name="Character",
        description="Your character armature",
        type=bpy.types.Object,
        poll=_poll_armature,
    )
    hide_source_after_retarget: BoolProperty(
        name="Hide Source Rig After Bake",
        default=True,
    )
    retarget_action_name: StringProperty(
        name="Action Name",
        default="Motifect_Retarget",
    )

    retarget_slots: CollectionProperty(type=MotifectRetargetSlot)
    retarget_slot_index: IntProperty(name="Slot Index", default=0)

    status_message: StringProperty(name="Status", default="Ready")
    is_busy: BoolProperty(name="Busy", default=False)
    credit_balance: IntProperty(name="Credits", default=-1)
    last_work_id: StringProperty(name="Last Work ID", default="")
    loading_progress_pct: IntProperty(name="Progress", default=0, min=0, max=100)
    loading_status: StringProperty(name="Loading Status", default="")
    loading_elapsed_text: StringProperty(name="Elapsed", default="0:00")


def register():
    from .registration import register_class

    unregister()
    register_class(MotifectRetargetSlot)
    register_class(MotifectProperties)
    bpy.types.Scene.motifect = PointerProperty(type=MotifectProperties)


def unregister():
    from .registration import unregister_class

    if hasattr(bpy.types.Scene, "motifect"):
        del bpy.types.Scene.motifect
    unregister_class(MotifectProperties)
    unregister_class(MotifectRetargetSlot)
