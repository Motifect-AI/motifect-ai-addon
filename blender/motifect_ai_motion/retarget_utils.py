# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Motifect

"""Retargeting — bind calibration + local rotation (frontend viewer.js parity)."""

from __future__ import annotations

import re

import bpy
from mathutils import Euler, Quaternion, Vector

# Same slots as frontend/src/shared/utils/retargetingBones.js (body only).
RETARGET_SLOTS: tuple[dict[str, object], ...] = (
    {"id": "pelvis", "label": "Pelvis / Hips", "required": True},
    {"id": "spine1", "label": "Spine", "required": True},
    {"id": "spine2", "label": "Chest", "required": False},
    {"id": "spine3", "label": "Upper Chest", "required": False},
    {"id": "neck", "label": "Neck", "required": False},
    {"id": "head", "label": "Head", "required": True},
    {"id": "left_collar", "label": "Left Collar", "required": False},
    {"id": "right_collar", "label": "Right Collar", "required": False},
    {"id": "left_shoulder", "label": "Left Upper Arm", "required": True},
    {"id": "right_shoulder", "label": "Right Upper Arm", "required": True},
    {"id": "left_elbow", "label": "Left Lower Arm", "required": True},
    {"id": "right_elbow", "label": "Right Lower Arm", "required": True},
    {"id": "left_wrist", "label": "Left Hand", "required": True},
    {"id": "right_wrist", "label": "Right Hand", "required": True},
    {"id": "left_hip", "label": "Left Upper Leg", "required": True},
    {"id": "right_hip", "label": "Right Upper Leg", "required": True},
    {"id": "left_knee", "label": "Left Lower Leg", "required": True},
    {"id": "right_knee", "label": "Right Lower Leg", "required": True},
    {"id": "left_ankle", "label": "Left Foot", "required": True},
    {"id": "right_ankle", "label": "Right Foot", "required": True},
    {"id": "left_foot", "label": "Left Toes", "required": False},
    {"id": "right_foot", "label": "Right Toes", "required": False},
)

RETARGET_SLOT_IDS: tuple[str, ...] = tuple(str(s["id"]) for s in RETARGET_SLOTS)
REQUIRED_SLOT_IDS: frozenset[str] = frozenset(
    str(s["id"]) for s in RETARGET_SLOTS if s.get("required")
)

# viewer.js JOINT_ROTATION_ORDER (body)
CALIBRATION_SLOT_ORDER: tuple[str, ...] = (
    "pelvis",
    "spine1",
    "spine2",
    "spine3",
    "neck",
    "left_collar",
    "left_shoulder",
    "left_elbow",
    "right_collar",
    "right_shoulder",
    "right_elbow",
    "left_hip",
    "left_knee",
    "left_ankle",
    "right_hip",
    "right_knee",
    "right_ankle",
    "left_wrist",
    "right_wrist",
    "head",
    "left_foot",
    "right_foot",
)

ROTATION_SKIP_SLOTS: frozenset[str] = frozenset({"left_foot", "right_foot"})

# viewer.js TARGET_LOCAL_ROTATION_CORRECTIONS.motifect (ankle roll fix)
_ANKLE_CORRECTION = Euler((4 * 3.14159265 / 180, 0, 0), "XYZ").to_quaternion()

TARGET_LOCAL_ROTATION_CORRECTIONS: dict[str, Quaternion] = {
    "left_ankle": _ANKLE_CORRECTION,
    "right_ankle": _ANKLE_CORRECTION,
}

BONE_ALIASES: dict[str, tuple[str, ...]] = {
    "pelvis": ("pelvis", "hips", "hip", "root", "mixamorighips", "Hips"),
    "left_hip": ("left_hip", "leftupleg", "leftupperleg", "LeftLeg", "LeftUpLeg"),
    "right_hip": ("right_hip", "rightupleg", "rightupperleg", "RightLeg", "RightUpLeg"),
    "spine1": ("spine1", "spine", "Spine1", "mixamorigspine"),
    "spine2": ("spine2", "chest", "Spine2", "mixamorigspine1"),
    "spine3": ("spine3", "upperchest", "Chest", "mixamorigspine2"),
    "neck": ("neck", "neck1", "neck2", "Neck1", "Neck2", "mixamorigneck"),
    "head": ("head", "Head", "mixamorighead"),
    "left_collar": ("left_collar", "leftshoulder", "LeftCollar", "LeftShoulder"),
    "right_collar": ("right_collar", "rightshoulder", "RightCollar", "RightShoulder"),
    "left_shoulder": ("left_shoulder", "leftarm", "LeftArm", "mixamorigleftarm"),
    "right_shoulder": ("right_shoulder", "rightarm", "RightArm", "mixamorigrightarm"),
    "left_elbow": ("left_elbow", "leftforearm", "LeftForeArm", "mixamorigleftforearm"),
    "right_elbow": ("right_elbow", "rightforearm", "RightForeArm", "mixamorigrightforearm"),
    "left_wrist": ("left_wrist", "lefthand", "LeftHand", "mixamoriglefthand"),
    "right_wrist": ("right_wrist", "righthand", "RightHand", "mixamorigrighthand"),
    "left_knee": ("left_knee", "leftshin", "LeftShin", "mixamorigleftleg"),
    "right_knee": ("right_knee", "rightshin", "RightShin", "mixamorigrightleg"),
    "left_ankle": ("left_ankle", "leftfoot", "LeftFoot", "mixamorigleftfoot"),
    "right_ankle": ("right_ankle", "rightfoot", "RightFoot", "mixamorigrightfoot"),
    "left_foot": ("left_foot", "lefttoe", "lefttoebase", "LeftToeBase"),
    "right_foot": ("right_foot", "righttoe", "righttoebase", "RightToeBase"),
}

BIND_LOC_KEY = "motifect_bind_location"
BIND_ROT_KEY = "motifect_bind_rotation"
UNMAPPED_BONE = ""


class RetargetError(Exception):
    pass


def bone_is_mapped(name: str) -> bool:
    return bool(name)


def normalize_bone_name(name: str) -> str:
    normalized = re.sub(r"[^a-z0-9]", "", (name or "").lower())
    for prefix in ("mixamorig", "def", "org", "mch"):
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix) :]
    return normalized


def ensure_retarget_slot_items(props) -> None:
    if props is None:
        return
    if len(props.retarget_slots) == len(RETARGET_SLOTS):
        return
    props.retarget_slots.clear()
    for slot in RETARGET_SLOTS:
        item = props.retarget_slots.add()
        item.slot_id = str(slot["id"])
        item.label = str(slot["label"])
        item.required = bool(slot.get("required"))
        item.source_bone = UNMAPPED_BONE
        item.target_bone = UNMAPPED_BONE


def apply_autofill_to_props(props) -> int:
    ensure_retarget_slot_items(props)
    filled = autofill_slot_mappings(props.source_armature, props.target_armature)
    count = 0
    for item in props.retarget_slots:
        src, tgt = filled.get(item.slot_id, (UNMAPPED_BONE, UNMAPPED_BONE))
        if src != UNMAPPED_BONE:
            item.source_bone = src
            count += 1
        if tgt != UNMAPPED_BONE:
            item.target_bone = tgt
            count += 1
    return count


def guess_slot_for_bone(bone_name: str) -> str | None:
    normalized = normalize_bone_name(bone_name)
    if not normalized:
        return None
    for slot_id, aliases in BONE_ALIASES.items():
        for alias in aliases:
            if normalize_bone_name(alias) == normalized:
                return slot_id
    return None


def autofill_slot_mappings(
    source_armature: bpy.types.Object | None,
    target_armature: bpy.types.Object | None,
) -> dict[str, tuple[str, str]]:
    result: dict[str, tuple[str, str]] = {
        slot_id: (UNMAPPED_BONE, UNMAPPED_BONE) for slot_id in RETARGET_SLOT_IDS
    }
    used_source: set[str] = set()
    used_target: set[str] = set()

    for armature, side in ((source_armature, "source"), (target_armature, "target")):
        if not armature or armature.type != "ARMATURE":
            continue
        for bone in armature.data.bones:
            slot_id = guess_slot_for_bone(bone.name)
            if not slot_id:
                continue
            src, tgt = result[slot_id]
            if side == "source":
                if src != UNMAPPED_BONE or bone.name in used_source:
                    continue
                result[slot_id] = (bone.name, tgt)
                used_source.add(bone.name)
            else:
                if tgt != UNMAPPED_BONE or bone.name in used_target:
                    continue
                result[slot_id] = (src, bone.name)
                used_target.add(bone.name)

    if source_armature and result["pelvis"][0] == UNMAPPED_BONE:
        for fallback in ("Hips", "Spine1", "pelvis", "root"):
            if fallback in source_armature.data.bones:
                src, tgt = result["pelvis"]
                result["pelvis"] = (fallback, tgt)
                break

    return result


def mappings_from_slot_items(slot_items) -> list[tuple[str, str, str]]:
    mappings: list[tuple[str, str, str]] = []
    for item in slot_items:
        if not bone_is_mapped(item.source_bone) or not bone_is_mapped(item.target_bone):
            continue
        mappings.append((item.slot_id, item.target_bone, item.source_bone))
    return mappings


def validate_mappings(
    source_armature: bpy.types.Object,
    target_armature: bpy.types.Object,
    mappings: list[tuple[str, str, str]],
) -> None:
    if source_armature.type != "ARMATURE" or target_armature.type != "ARMATURE":
        raise RetargetError("Source and target must be armatures.")
    if source_armature == target_armature:
        raise RetargetError("Source and target must be different armatures.")
    if not source_armature.animation_data or not source_armature.animation_data.action:
        raise RetargetError("Source armature has no animation.")

    mapped_slots = {slot_id for slot_id, _, _ in mappings}
    missing = [slot_id for slot_id in REQUIRED_SLOT_IDS if slot_id not in mapped_slots]
    if missing:
        raise RetargetError(f"Required bone slots not mapped: {', '.join(missing)}")
    if not mappings:
        raise RetargetError("No bone mappings. Use Auto-fill or map bones manually.")


def _update_view_layer() -> None:
    bpy.context.view_layer.update()


def _ensure_quaternion_mode(armature_obj: bpy.types.Object, bone_names: list[str]) -> None:
    for name in bone_names:
        pb = armature_obj.pose.bones.get(name)
        if pb is None:
            continue
        if pb.rotation_mode != "QUATERNION":
            pb.rotation_mode = "QUATERNION"


def _bone_world_position(armature_obj: bpy.types.Object, bone_name: str) -> Vector:
    pb = armature_obj.pose.bones.get(bone_name)
    if pb is None:
        return Vector((0.0, 0.0, 0.0))
    return armature_obj.matrix_world @ pb.matrix @ Vector((0.0, 0.0, 0.0))


def _bone_world_rotation(armature_obj: bpy.types.Object, bone_name: str) -> Quaternion:
    pb = armature_obj.pose.bones.get(bone_name)
    if pb is None:
        return Quaternion()
    return (armature_obj.matrix_world @ pb.matrix).to_quaternion()


def _parent_world_rotation(armature_obj: bpy.types.Object, pose_bone: bpy.types.PoseBone) -> Quaternion:
    if pose_bone.parent:
        return _bone_world_rotation(armature_obj, pose_bone.parent.name)
    return armature_obj.matrix_world.to_quaternion()


def _capture_rest_local_rotations(armature_obj: bpy.types.Object, bone_names: list[str]) -> dict[str, Quaternion]:
    prev = armature_obj.data.pose_position
    armature_obj.data.pose_position = "REST"
    _update_view_layer()
    rest: dict[str, Quaternion] = {}
    for name in bone_names:
        pb = armature_obj.pose.bones.get(name)
        if pb is not None:
            rest[name] = pb.rotation_quaternion.copy()
    armature_obj.data.pose_position = prev
    _update_view_layer()
    return rest


def _slot_to_bones(mappings: list[tuple[str, str, str]]) -> tuple[dict[str, str], dict[str, str]]:
    source: dict[str, str] = {}
    target: dict[str, str] = {}
    for slot_id, tgt, src in mappings:
        source[slot_id] = src
        target[slot_id] = tgt
    return source, target


def _build_pelvis_world_position(
    source_armature: bpy.types.Object,
    slot_to_source: dict[str, str],
) -> Vector | None:
    pelvis_bone = slot_to_source.get("pelvis")
    if pelvis_bone:
        return _bone_world_position(source_armature, pelvis_bone)

    left = slot_to_source.get("left_hip")
    right = slot_to_source.get("right_hip")
    if left and right:
        return (_bone_world_position(source_armature, left) + _bone_world_position(source_armature, right)) * 0.5

    spine = slot_to_source.get("spine1")
    if spine:
        return _bone_world_position(source_armature, spine)
    return None


def _measure_height(armature_obj: bpy.types.Object, slot_to_bone: dict[str, str]) -> float:
    pelvis = slot_to_bone.get("pelvis") or slot_to_bone.get("spine1")
    head = slot_to_bone.get("head")
    if not pelvis:
        return 1.0
    prev = armature_obj.data.pose_position
    armature_obj.data.pose_position = "REST"
    _update_view_layer()
    p = _bone_world_position(armature_obj, pelvis)
    if head:
        height = (_bone_world_position(armature_obj, head) - p).length
    else:
        height = abs(p.z)
    armature_obj.data.pose_position = prev
    _update_view_layer()
    return max(height, 1e-4)


def _build_slot_calibrations(
    source_armature: bpy.types.Object,
    target_armature: bpy.types.Object,
    slot_to_source: dict[str, str],
    slot_to_target: dict[str, str],
) -> dict[str, tuple[Quaternion, Quaternion]]:
    """viewer.js precomputedRetargetQuats: targetLocal = left @ srcLocal @ right."""
    prev_src = source_armature.data.pose_position
    prev_tgt = target_armature.data.pose_position
    source_armature.data.pose_position = "REST"
    target_armature.data.pose_position = "REST"
    _update_view_layer()

    calibrations: dict[str, tuple[Quaternion, Quaternion]] = {}
    for slot_id in CALIBRATION_SLOT_ORDER:
        src_name = slot_to_source.get(slot_id)
        tgt_name = slot_to_target.get(slot_id)
        if not src_name or not tgt_name:
            continue

        src_pb = source_armature.pose.bones.get(src_name)
        tgt_pb = target_armature.pose.bones.get(tgt_name)
        if src_pb is None or tgt_pb is None:
            continue

        bind_src_world = _bone_world_rotation(source_armature, src_name)
        bind_trg_world = _bone_world_rotation(target_armature, tgt_name)
        bind_src_parent = _parent_world_rotation(source_armature, src_pb)
        bind_trg_parent = _parent_world_rotation(target_armature, tgt_pb)

        left = bind_trg_parent.inverted() @ bind_src_parent
        right = bind_src_world.inverted() @ bind_trg_world
        calibrations[slot_id] = (left.normalized(), right.normalized())

    source_armature.data.pose_position = prev_src
    target_armature.data.pose_position = prev_tgt
    _update_view_layer()
    return calibrations


def _apply_calibration_pose(
    target_armature: bpy.types.Object,
    source_armature: bpy.types.Object,
    *,
    slot_to_source: dict[str, str],
    slot_to_target: dict[str, str],
    target_rest_local: dict[str, Quaternion],
    calibrations: dict[str, tuple[Quaternion, Quaternion]],
) -> None:
    """Apply one frame using bind calibrations (viewer.js applyAvatarPose localRotations path)."""
    for slot_id in CALIBRATION_SLOT_ORDER:
        if slot_id in ROTATION_SKIP_SLOTS:
            continue

        src_name = slot_to_source.get(slot_id)
        tgt_name = slot_to_target.get(slot_id)
        calibration = calibrations.get(slot_id)
        if not src_name or not tgt_name or calibration is None:
            continue

        src_pb = source_armature.pose.bones.get(src_name)
        tgt_pb = target_armature.pose.bones.get(tgt_name)
        if src_pb is None or tgt_pb is None:
            continue

        left, right = calibration
        src_local = src_pb.rotation_quaternion.copy()
        target_local = (left @ src_local @ right).normalized()

        correction = TARGET_LOCAL_ROTATION_CORRECTIONS.get(slot_id)
        if correction is not None:
            target_local = (target_local @ correction).normalized()

        tgt_pb.rotation_quaternion = target_local


def _get_frame_range(source_armature: bpy.types.Object) -> tuple[int, int]:
    action = source_armature.animation_data.action
    start = int(action.frame_range[0])
    end = int(action.frame_range[1])
    if end <= start:
        end = start + 1
    return start, end


def _capture_bind(armature_obj: bpy.types.Object, frame: int) -> tuple[Vector, Vector]:
    scene = bpy.context.scene
    prev = scene.frame_current
    scene.frame_set(frame)
    _update_view_layer()
    loc = armature_obj.location.copy()
    rot = armature_obj.rotation_euler.copy()
    scene.frame_set(prev)
    _update_view_layer()
    return loc, rot


def _reset_pose(armature_obj: bpy.types.Object) -> None:
    armature_obj.data.pose_position = "REST"
    _update_view_layer()
    armature_obj.data.pose_position = "POSE"
    _update_view_layer()
    for pb in armature_obj.pose.bones:
        if pb.rotation_mode != "QUATERNION":
            pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion.identity()
        pb.location.zero()
        pb.scale = (1.0, 1.0, 1.0)
    _update_view_layer()


def clear_retarget_action(target_armature: bpy.types.Object, action_name: str | None = None) -> None:
    if action_name:
        for action in list(bpy.data.actions):
            if action.name == action_name or action.name.startswith(f"{action_name}."):
                if target_armature.animation_data and target_armature.animation_data.action == action:
                    target_armature.animation_data.action = None
                if action.users == 0:
                    bpy.data.actions.remove(action)
    if target_armature.animation_data:
        target_armature.animation_data.action = None
    if BIND_LOC_KEY in target_armature:
        target_armature.location = Vector(target_armature[BIND_LOC_KEY])
        target_armature.rotation_euler = Vector(target_armature[BIND_ROT_KEY])
    _reset_pose(target_armature)


def hide_armature_objects(root_armature: bpy.types.Object) -> None:
    root_armature.hide_set(True)
    root_armature.hide_render = True
    for child in root_armature.children:
        child.hide_set(True)
        child.hide_render = True


def bake_retarget(
    source_armature: bpy.types.Object,
    target_armature: bpy.types.Object,
    mappings: list[tuple[str, str, str]],
    action_name: str,
) -> bpy.types.Action:
    """Bake with bind-pose calibration retarget (site motion viewer parity)."""
    validate_mappings(source_armature, target_armature, mappings)
    slot_to_source, slot_to_target = _slot_to_bones(mappings)

    if "pelvis" not in slot_to_source or "pelvis" not in slot_to_target:
        raise RetargetError("Map pelvis / hips on both Source and Character.")

    frame_start, frame_end = _get_frame_range(source_armature)
    scene = bpy.context.scene
    prev_frame = scene.frame_current

    target_bones = list({tgt for _, tgt, _ in mappings})
    source_bones = list({src for _, _, src in mappings})
    _ensure_quaternion_mode(source_armature, source_bones)
    _ensure_quaternion_mode(target_armature, target_bones)

    if target_armature.animation_data is None:
        target_armature.animation_data_create()
    clear_retarget_action(target_armature, action_name)

    bind_loc, bind_rot = _capture_bind(target_armature, frame_start)
    if BIND_LOC_KEY not in target_armature:
        target_armature[BIND_LOC_KEY] = list(bind_loc)
        target_armature[BIND_ROT_KEY] = list(bind_rot)
    else:
        bind_loc = Vector(target_armature[BIND_LOC_KEY])
        bind_rot = Vector(target_armature[BIND_ROT_KEY])
    target_armature.location = bind_loc
    target_armature.rotation_euler = bind_rot

    target_rest_local = _capture_rest_local_rotations(target_armature, target_bones)
    calibrations = _build_slot_calibrations(
        source_armature, target_armature, slot_to_source, slot_to_target
    )
    if not calibrations:
        raise RetargetError("Could not build bind calibrations — check bone mappings.")

    source_height = _measure_height(source_armature, slot_to_source)
    target_height = _measure_height(target_armature, slot_to_target)
    translation_scale = target_height / source_height

    tgt_pelvis_bone = slot_to_target["pelvis"]
    tgt_pelvis_rest_loc = target_armature.pose.bones[tgt_pelvis_bone].location.copy()

    source_armature.data.pose_position = "POSE"
    target_armature.data.pose_position = "POSE"

    scene.frame_set(frame_start)
    _update_view_layer()
    rest_pelvis_world = _build_pelvis_world_position(source_armature, slot_to_source)
    if rest_pelvis_world is None:
        raise RetargetError("Could not resolve source pelvis position.")

    action = bpy.data.actions.new(name=action_name)
    target_armature.animation_data.action = action

    try:
        for frame in range(frame_start, frame_end + 1):
            scene.frame_set(frame)
            _update_view_layer()

            pelvis_pos = _build_pelvis_world_position(source_armature, slot_to_source)
            if pelvis_pos is not None:
                root_offset = (pelvis_pos - rest_pelvis_world) * translation_scale
                target_armature.location = bind_loc + root_offset

            for tgt_bone in target_bones:
                pb = target_armature.pose.bones.get(tgt_bone)
                rest_q = target_rest_local.get(tgt_bone)
                if pb and rest_q:
                    pb.rotation_quaternion = rest_q.copy()
            tgt_pb = target_armature.pose.bones.get(tgt_pelvis_bone)
            if tgt_pb:
                tgt_pb.location = tgt_pelvis_rest_loc.copy()
            _update_view_layer()

            _apply_calibration_pose(
                target_armature,
                source_armature,
                slot_to_source=slot_to_source,
                slot_to_target=slot_to_target,
                target_rest_local=target_rest_local,
                calibrations=calibrations,
            )

            for tgt_bone in target_bones:
                pb = target_armature.pose.bones.get(tgt_bone)
                if pb:
                    pb.keyframe_insert(data_path="rotation_quaternion", frame=frame)
            target_armature.pose.bones[tgt_pelvis_bone].keyframe_insert(data_path="location", frame=frame)
            target_armature.keyframe_insert(data_path="location", frame=frame)
    finally:
        scene.frame_set(prev_frame)
        _update_view_layer()

    return action
