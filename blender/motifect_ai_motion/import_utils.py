# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Motifect

import re

import bpy

EXPORT_FORMAT = "fbx"
COLLECTION_NAME = "Motifect"


def slugify_prompt(prompt: str, max_len: int = 24) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", prompt.strip().lower()).strip("_")
    return (slug[:max_len] if slug else "motion")


def build_import_name(work_id: str, prompt: str) -> str:
    short_id = work_id.replace("wrk_", "")[:8]
    return f"Motifect_{slugify_prompt(prompt)}_{short_id}"


def get_or_create_collection(name: str = COLLECTION_NAME) -> bpy.types.Collection:
    collection = bpy.data.collections.get(name)
    if collection is None:
        collection = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(collection)
    return collection


def _import_fbx(filepath: str) -> set[bpy.types.Object]:
    existing = set(bpy.data.objects)
    kwargs = {
        "filepath": filepath,
        "automatic_bone_orientation": True,
        "use_anim": True,
    }
    if hasattr(bpy.ops.import_scene, "fbx"):
        bpy.ops.import_scene.fbx(**kwargs)
    else:
        bpy.ops.wm.fbx_import(**kwargs)
    return {obj for obj in bpy.data.objects if obj not in existing}


def organize_imported_objects(
    imported_objects: set[bpy.types.Object],
    work_id: str,
    prompt: str,
) -> bpy.types.Object | None:
    if not imported_objects:
        return None

    base_name = build_import_name(work_id, prompt)
    collection = get_or_create_collection()

    armature = next((obj for obj in imported_objects if obj.type == "ARMATURE"), None)

    for obj in imported_objects:
        for user_collection in list(obj.users_collection):
            user_collection.objects.unlink(obj)
        collection.objects.link(obj)

    if armature is None:
        return None

    armature.name = base_name
    if armature.animation_data and armature.animation_data.action:
        armature.animation_data.action.name = f"{base_name}_Action"

    for child in armature.children:
        if child.type == "MESH":
            child.name = f"{base_name}_Mesh"

    for obj in imported_objects:
        if obj != armature and obj.type not in {"ARMATURE", "MESH"}:
            obj.name = f"{base_name}_{obj.type.title()}"

    return armature


def import_motion_fbx(filepath: str, work_id: str, prompt: str) -> bpy.types.Object | None:
    imported = _import_fbx(filepath)
    return organize_imported_objects(imported, work_id, prompt)
