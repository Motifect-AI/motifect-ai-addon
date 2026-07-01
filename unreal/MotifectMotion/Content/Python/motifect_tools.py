"""Motifect Unreal Editor tools — generate and import motion via REST API."""

from __future__ import annotations

import json
import os
import tempfile
import threading
import traceback
from typing import Callable

import unreal

from motifect_client import MotifectAPIError, MotifectClient

MENU_OWNER = "MotifectMotion"
CONFIG_DIR_NAME = "Motifect"
DEFAULT_DESTINATION = "/Game/Motifect/Animations"
DEFAULT_PROMPT = "A person turns sharply, regains balance, and continues walking."

_active_poll: dict | None = None
_tick_handle = None


def _project_saved_dir() -> str:
    project_dir = unreal.Paths.project_saved_dir()
    path = os.path.join(project_dir, CONFIG_DIR_NAME)
    os.makedirs(path, exist_ok=True)
    return path


def _config_path() -> str:
    return os.path.join(_project_saved_dir(), "config.json")


def load_config() -> dict:
    path = _config_path()
    if not os.path.isfile(path):
        return {
            "api_key": "",
            "api_base_url": "https://api.motifect.io/api/v1",
            "prompt": DEFAULT_PROMPT,
            "duration_seconds": 8,
            "model_key": "motifect-v3",
            "export_format": "fbx",
            "import_destination": DEFAULT_DESTINATION,
        }
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def save_config(config: dict) -> None:
    with open(_config_path(), "w", encoding="utf-8") as handle:
        json.dump(config, handle, indent=2)
    unreal.log(f"[Motifect] Saved config: {_config_path()}")


def _make_client(config: dict) -> MotifectClient:
    api_key = (config.get("api_key") or os.environ.get("MOTIFECT_API_KEY") or "").strip()
    if not api_key:
        raise MotifectAPIError(
            "API key missing. Set api_key in Saved/Motifect/config.json or MOTIFECT_API_KEY env var."
        )
    return MotifectClient(api_key, config.get("api_base_url", "https://api.motifect.io/api/v1"))


def import_motion_file(filepath: str, destination: str = DEFAULT_DESTINATION) -> list[str]:
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()

    task = unreal.AssetImportTask()
    task.filename = filepath
    task.destination_path = destination
    task.automated = True
    task.save = True
    task.replace_existing = True

    ui = unreal.FbxImportUI()
    ui.import_mesh = True
    ui.import_animations = True
    ui.import_materials = False
    ui.import_textures = False
    ui.automated_import_should_detect_type = True

    task.options = ui
    asset_tools.import_asset_tasks([task])
    paths = list(task.imported_object_paths or [])
    unreal.log(f"[Motifect] Imported: {paths}")
    return paths


def _notify(title: str, message: str) -> None:
    unreal.log(f"[Motifect] {title}: {message}")
    try:
        unreal.EditorDialog.show_message(title, message, unreal.AppMsgType.OK)
    except Exception:
        pass


def check_balance() -> None:
    try:
        config = load_config()
        client = _make_client(config)
        payload = client.get_balance()
        balance = payload.get("balance", 0)
        _notify("Motifect Credits", f"Current balance: {balance}")
    except Exception as exc:
        _notify("Motifect Error", str(exc))


def open_config_folder() -> None:
    path = _project_saved_dir()
    save_config(load_config())
    unreal.log(f"[Motifect] Edit config here: {_config_path()}")
    _notify(
        "Motifect Config",
        f"Edit this file, then save:\n\n{_config_path()}\n\nSet api_key to your mk_live_... key.",
    )


def _stop_poll() -> None:
    global _tick_handle, _active_poll
    if _tick_handle is not None:
        unreal.unregister_slate_post_tick_callback(_tick_handle)
        _tick_handle = None
    _active_poll = None


def _poll_tick(delta_time: float) -> bool:
    state = _active_poll
    if not state:
        return False

    elapsed = state.get("elapsed", 0.0) + delta_time
    state["elapsed"] = elapsed
    interval = state.get("poll_interval", 3.0)
    if elapsed < state.get("next_poll_at", 0.0):
        return True

    state["next_poll_at"] = elapsed + interval
    client: MotifectClient = state["client"]
    work_id = state["work_id"]
    export_format = state["export_format"]
    temp_path = state["temp_path"]
    destination = state["destination"]

    try:
        payload = client.get_motion(work_id)
        work = payload["item"]
        status = work.get("status", "unknown")
        unreal.log(f"[Motifect] {work_id}: {MotifectClient.format_work_status(work)}")

        if status == "completed":
            url = MotifectClient.find_asset_url(work, export_format, asset_role="export_file")
            if not url:
                convert_payload = client.convert(work_id, export_format)
                work = convert_payload["item"]
                url = MotifectClient.find_asset_url(work, export_format, asset_role="export_file")
            if not url:
                raise MotifectAPIError(f"No {export_format.upper()} export available")

            client.download(url, temp_path)

            def do_import():
                try:
                    import_motion_file(temp_path, destination)
                    _notify("Motifect", f"Motion imported ({work_id})")
                finally:
                    if os.path.isfile(temp_path):
                        os.remove(temp_path)
                    _stop_poll()

            unreal.call_in_editor_thread(do_import)
            return True

        if status == "failed":
            summary = work.get("error_summary") or "Generation failed"
            raise MotifectAPIError(summary)

    except Exception as exc:
        unreal.log_error(f"[Motifect] {exc}")
        traceback.print_exc()
        _notify("Motifect Error", str(exc))
        if os.path.isfile(temp_path):
            os.remove(temp_path)
        _stop_poll()
        return False

    return True


def generate_motion(
    prompt: str | None = None,
    duration_seconds: int | None = None,
    model_key: str | None = None,
    export_format: str | None = None,
    destination: str | None = None,
) -> None:
    global _active_poll, _tick_handle

    if _active_poll is not None:
        _notify("Motifect", "A generation is already running.")
        return

    config = load_config()
    prompt = (prompt or config.get("prompt") or DEFAULT_PROMPT).strip()
    duration_seconds = duration_seconds or int(config.get("duration_seconds", 8))
    model_key = model_key or config.get("model_key", "motifect-v3")
    export_format = export_format or config.get("export_format", "fbx")
    destination = destination or config.get("import_destination", DEFAULT_DESTINATION)

    if len(prompt) < 10:
        _notify("Motifect Error", "Prompt must be at least 10 characters.")
        return

    try:
        client = _make_client(config)
    except Exception as exc:
        _notify("Motifect Error", str(exc))
        return

    suffix = f".{export_format}"
    temp_fd, temp_path = tempfile.mkstemp(suffix=suffix, prefix="motifect_")
    os.close(temp_fd)

    try:
        gen = client.generate(prompt, duration_seconds, model_key)
        work_id = gen["data"]["work"]["id"]
    except Exception as exc:
        os.remove(temp_path)
        _notify("Motifect Error", str(exc))
        return

    unreal.log(f"[Motifect] Queued {work_id}: {prompt[:60]}...")
    _active_poll = {
        "client": client,
        "work_id": work_id,
        "export_format": export_format,
        "temp_path": temp_path,
        "destination": destination,
        "poll_interval": 3.0,
        "elapsed": 0.0,
        "next_poll_at": 1.0,
    }
    _tick_handle = unreal.register_slate_post_tick_callback(_poll_tick)


def generate_motion_blocking(
    prompt: str | None = None,
    duration_seconds: int | None = None,
    model_key: str | None = None,
    export_format: str = "fbx",
    destination: str | None = None,
    on_progress: Callable[[dict], None] | None = None,
) -> dict:
    """Blocking helper for scripts / automation."""
    config = load_config()
    prompt = (prompt or config.get("prompt") or DEFAULT_PROMPT).strip()
    duration_seconds = duration_seconds or int(config.get("duration_seconds", 8))
    model_key = model_key or config.get("model_key", "motifect-v3")
    destination = destination or config.get("import_destination", DEFAULT_DESTINATION)

    client = _make_client(config)
    suffix = f".{export_format}"
    temp_fd, temp_path = tempfile.mkstemp(suffix=suffix, prefix="motifect_")
    os.close(temp_fd)

    try:
        work = client.generate_and_export(
            prompt=prompt,
            dest_path=temp_path,
            export_format=export_format,
            duration_seconds=duration_seconds,
            model_key=model_key,
            on_progress=on_progress,
        )
        import_motion_file(temp_path, destination)
        return work
    finally:
        if os.path.isfile(temp_path):
            os.remove(temp_path)


def _register_menus() -> None:
    menus = unreal.ToolMenus.get()
    if menus is None:
        unreal.log_warning("[Motifect] ToolMenus unavailable")
        return

    owner = unreal.Name(MENU_OWNER)
    main_menu = menus.extend_menu("LevelEditor.MainMenu.Tools")
    main_menu.add_sub_menu(owner, "Motifect", unreal.Name("Motifect"), "Motifect")

    entries = [
        ("Generate Motion", "import motifect_tools; motifect_tools.generate_motion()"),
        ("Check Credits", "import motifect_tools; motifect_tools.check_balance()"),
        ("Open Config Folder", "import motifect_tools; motifect_tools.open_config_folder()"),
    ]

    for label, command in entries:
        entry = unreal.ToolMenuEntry(
            name=f"Motifect_{label.replace(' ', '')}",
            type=unreal.MultiBlockType.MENU_ENTRY,
            insert_position=unreal.ToolMenuInsert("", unreal.ToolMenuInsertType.DEFAULT),
        )
        entry.set_label(label)
        entry.set_string_command(
            unreal.ToolMenuStringCommand(
                type=unreal.ToolMenuStringCommandType.PYTHON,
                custom_type=unreal.Name(""),
                string=command,
            )
        )
        main_menu.add_menu_entry("Motifect", entry)

    menus.refresh_all_widgets()
    unreal.log("[Motifect] Tools menu registered")


def register() -> None:
    _register_menus()


def unregister() -> None:
    _stop_poll()
