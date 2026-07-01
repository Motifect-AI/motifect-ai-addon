# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Motifect

import os
import tempfile
import time
import traceback

import bpy
from bpy.types import Operator

from .import_utils import EXPORT_FORMAT, import_motion_fbx
from .motifect_client import MotifectAPIError, MotifectClient
from .preferences import get_preferences
from .version import RETARGET_ENABLED

if RETARGET_ENABLED:
    from .retarget_utils import (
        RetargetError,
        apply_autofill_to_props,
        bake_retarget,
        clear_retarget_action,
        ensure_retarget_slot_items,
        hide_armature_objects,
        mappings_from_slot_items,
    )

POLL_STATE = {}
UI_REFRESH_INTERVAL = 0.5


def _format_elapsed(seconds: float) -> str:
    total = max(0, int(seconds))
    minutes, secs = divmod(total, 60)
    return f"{minutes}:{secs:02d}"


def _tag_redraw_view3d():
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()


def _estimate_progress(work: dict, elapsed: float) -> int:
    status = work.get("status", "unknown")
    if status == "queued":
        return min(30, int(8 + elapsed * 0.2))
    if status == "processing":
        return min(92, int(32 + elapsed * 0.9))
    if status == "completed":
        return 100
    return min(12, int(elapsed))


def _set_loading_state(props, work: dict | None = None):
    if work is None:
        props.loading_progress_pct = 5
        props.loading_status = "Submitting request…"
        props.loading_elapsed_text = "0:00"
        return

    props.loading_status = MotifectClient.format_work_status(work)
    started_at = POLL_STATE.get("started_at", time.monotonic())
    elapsed = time.monotonic() - started_at
    props.loading_elapsed_text = _format_elapsed(elapsed)
    props.loading_progress_pct = _estimate_progress(work, elapsed)


def _format_error(exc: Exception) -> str:
    if isinstance(exc, MotifectAPIError):
        if exc.diagnostics:
            response = exc.diagnostics.get("response", {})
            body = (response.get("body") or "").strip()
            if body and body not in str(exc):
                return f"{exc} | body: {body[:240]}"
        return str(exc)
    return str(exc)


def _log_error(context, exc: Exception):
    props = context.scene.motifect
    props.status_message = _format_error(exc)
    print(f"[Motifect] {props.status_message}")
    traceback.print_exc()


def _make_client(context) -> MotifectClient:
    prefs = get_preferences(context)
    if not prefs.api_key:
        raise MotifectAPIError("Set your API key in Edit → Preferences → Add-ons → Motifect Motion")
    return MotifectClient(prefs.api_key, prefs.api_base_url)


def refresh_credits(context, client: MotifectClient | None = None) -> int | None:
    props = context.scene.motifect
    try:
        api_client = client or _make_client(context)
        payload = api_client.get_balance()
        props.credit_balance = int(payload.get("balance", 0))
        return props.credit_balance
    except (MotifectAPIError, ValueError) as exc:
        print(f"[Motifect] Failed to refresh credits: {exc}")
        return None


def _initial_credit_refresh():
    try:
        context = bpy.context
        if context.scene and getattr(context.scene, "motifect", None):
            refresh_credits(context)
    except Exception as exc:
        print(f"[Motifect] Initial credit refresh skipped: {exc}")
    return None


def _poll_timer():
    state = POLL_STATE
    if not state:
        return None

    props = state["props"]
    client = state["client"]
    work_id = state["work_id"]
    prompt = state["prompt"]
    temp_path = state["temp_path"]
    context = state.get("context")

    try:
        payload = client.get_motion(work_id)
        work = payload["item"]
        state["last_work"] = work
        status = work.get("status", "unknown")
        props.status_message = MotifectClient.format_work_status(work)
        _set_loading_state(props, work)

        if status == "completed":
            props.loading_progress_pct = 95
            props.loading_status = "Downloading and importing FBX…"
            _tag_redraw_view3d()

            url = MotifectClient.find_asset_url(work, EXPORT_FORMAT, asset_role="export_file")
            if not url:
                convert_payload = client.convert(work_id, EXPORT_FORMAT)
                work = convert_payload["item"]
                url = MotifectClient.find_asset_url(work, EXPORT_FORMAT, asset_role="export_file")
            if not url:
                raise MotifectAPIError("No FBX export available")

            client.download(url, temp_path)
            armature = import_motion_fbx(temp_path, work_id, prompt)
            if armature:
                props.status_message = f"Imported {armature.name}"
            else:
                props.status_message = f"Imported FBX ({work_id})"

            props.loading_progress_pct = 100
            props.loading_status = props.status_message
            props.last_work_id = work_id
            if context:
                refresh_credits(context, client)
            return _finish(state)

        if status == "failed":
            summary = work.get("error_summary") or "Generation failed"
            raise MotifectAPIError(summary)

    except Exception as exc:
        if context:
            _log_error(context, exc)
        else:
            print(f"[Motifect] {exc}")
            traceback.print_exc()
        return _finish(state)

    return state.get("interval", 3.0)


def _finish(state):
    props = state.get("props")
    temp_path = state.get("temp_path")
    if props:
        props.is_busy = False
        props.loading_status = ""
        props.loading_progress_pct = 0
        props.loading_elapsed_text = "0:00"
    if temp_path and os.path.isfile(temp_path):
        try:
            os.remove(temp_path)
        except OSError:
            pass
    POLL_STATE.clear()
    return None


def _ui_refresh_timer():
    state = POLL_STATE
    if not state:
        return None

    props = state.get("props")
    if not props or not props.is_busy:
        return None

    started_at = state.get("started_at", time.monotonic())
    elapsed = time.monotonic() - started_at
    props.loading_elapsed_text = _format_elapsed(elapsed)

    work = state.get("last_work")
    if work:
        props.loading_progress_pct = _estimate_progress(work, elapsed)

    _tag_redraw_view3d()
    return UI_REFRESH_INTERVAL


class MOTIFECT_OT_refresh_credits(Operator):
    bl_idname = "motifect.refresh_credits"
    bl_label = "Refresh Credits"

    def execute(self, context):
        props = context.scene.motifect
        balance = refresh_credits(context)
        if balance is None:
            self.report({"ERROR"}, "Could not refresh credits")
            return {"CANCELLED"}
        props.status_message = "Ready"
        self.report({"INFO"}, f"Credits: {balance:,}")
        return {"FINISHED"}


class MOTIFECT_OT_generate_motion(Operator):
    bl_idname = "motifect.generate_motion"
    bl_label = "Generate Motion"
    bl_description = "Generate motion from prompt and import FBX"

    def execute(self, context):
        props = context.scene.motifect

        prompt = props.prompt.strip()
        if len(prompt) < 10:
            self.report({"ERROR"}, "Prompt must be at least 10 characters")
            return {"CANCELLED"}

        if props.is_busy or POLL_STATE:
            self.report({"WARNING"}, "A generation is already in progress")
            return {"CANCELLED"}

        try:
            client = _make_client(context)
        except (MotifectAPIError, ValueError) as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}

        temp_fd, temp_path = tempfile.mkstemp(suffix=".fbx", prefix="motifect_")
        os.close(temp_fd)

        try:
            gen = client.generate(
                prompt=prompt,
                duration_seconds=props.duration_seconds,
                model_key=props.model_key,
            )
            work_id = gen["data"]["work"]["id"]
        except MotifectAPIError as exc:
            os.remove(temp_path)
            _log_error(context, exc)
            self.report({"ERROR"}, _format_error(exc))
            return {"CANCELLED"}

        props.is_busy = True
        props.status_message = f"Queued ({work_id})"
        props.last_work_id = work_id
        _set_loading_state(props)

        POLL_STATE.clear()
        POLL_STATE.update(
            {
                "client": client,
                "work_id": work_id,
                "prompt": prompt,
                "temp_path": temp_path,
                "props": props,
                "context": context,
                "interval": 3.0,
                "started_at": time.monotonic(),
                "last_work": None,
            }
        )
        bpy.app.timers.register(_poll_timer, first_interval=1.0)
        bpy.app.timers.register(_ui_refresh_timer, first_interval=UI_REFRESH_INTERVAL)
        self.report({"INFO"}, f"Generating… {work_id}")
        return {"FINISHED"}


class MOTIFECT_OT_open_docs(Operator):
    bl_idname = "motifect.open_docs"
    bl_label = "Open API Docs"

    def execute(self, context):
        import webbrowser

        webbrowser.open("https://motifect.io/en/docs")
        return {"FINISHED"}


classes = (
    MOTIFECT_OT_refresh_credits,
    MOTIFECT_OT_generate_motion,
    MOTIFECT_OT_open_docs,
)

if RETARGET_ENABLED:

    class MOTIFECT_OT_autofill_mappings(Operator):
        bl_idname = "motifect.autofill_mappings"
        bl_label = "Auto-fill Bone Mappings"
        bl_description = "Guess bone slots from names (review and adjust like motifect.io)"

        def execute(self, context):
            props = context.scene.motifect
            ensure_retarget_slot_items(props)
            if not props.source_armature or not props.target_armature:
                self.report({"ERROR"}, "Set Source and Character armatures first")
                return {"CANCELLED"}

            count = apply_autofill_to_props(props)
            self.report({"INFO"}, f"Auto-filled {count} bone picks — review before Bake")
            return {"FINISHED"}

    class MOTIFECT_OT_bake_retarget(Operator):
        bl_idname = "motifect.bake_retarget"
        bl_label = "Bake Retarget"
        bl_description = "Bake animation with bind-pose calibration retarget"

        def execute(self, context):
            props = context.scene.motifect
            source = props.source_armature
            target = props.target_armature

            if not source or not target:
                self.report({"ERROR"}, "Set Source and Character armatures")
                return {"CANCELLED"}

            ensure_retarget_slot_items(props)
            mappings = mappings_from_slot_items(props.retarget_slots)
            action_name = props.retarget_action_name.strip() or f"{target.name}_Retarget"

            prev_active = context.view_layer.objects.active
            prev_mode = prev_active.mode if prev_active else "OBJECT"

            try:
                context.view_layer.objects.active = target
                bpy.ops.object.mode_set(mode="POSE")
                action = bake_retarget(source, target, mappings, action_name)
            except RetargetError as exc:
                self.report({"ERROR"}, str(exc))
                return {"CANCELLED"}
            finally:
                if prev_active:
                    context.view_layer.objects.active = prev_active
                    try:
                        bpy.ops.object.mode_set(mode=prev_mode)
                    except RuntimeError:
                        bpy.ops.object.mode_set(mode="OBJECT")

            if props.hide_source_after_retarget:
                hide_armature_objects(source)

            props.status_message = f"Baked {action.name} ({int(action.frame_range[1])} frames)"
            self.report({"INFO"}, props.status_message)
            return {"FINISHED"}

    class MOTIFECT_OT_clear_retarget(Operator):
        bl_idname = "motifect.clear_retarget"
        bl_label = "Clear Retarget"
        bl_description = "Remove baked retarget action and reset character pose"

        def execute(self, context):
            props = context.scene.motifect
            target = props.target_armature
            if not target:
                self.report({"ERROR"}, "Set Character armature")
                return {"CANCELLED"}

            action_name = props.retarget_action_name.strip() or f"{target.name}_Retarget"
            clear_retarget_action(target, action_name)
            props.status_message = f"Cleared retarget on {target.name}"
            self.report({"INFO"}, props.status_message)
            return {"FINISHED"}

    classes = classes + (
        MOTIFECT_OT_autofill_mappings,
        MOTIFECT_OT_bake_retarget,
        MOTIFECT_OT_clear_retarget,
    )

_initial_refresh_timer = None


def register():
    global _initial_refresh_timer
    from .registration import register_class

    for cls in classes:
        register_class(cls)
    _initial_refresh_timer = bpy.app.timers.register(_initial_credit_refresh, first_interval=1.0)


def unregister():
    global _initial_refresh_timer
    from .registration import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)
    POLL_STATE.clear()
    if _initial_refresh_timer is not None:
        try:
            bpy.app.timers.unregister(_initial_credit_refresh)
        except Exception:
            pass
        _initial_refresh_timer = None
