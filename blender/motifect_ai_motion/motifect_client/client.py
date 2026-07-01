# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Motifect

"""Motifect REST API client — no third-party dependencies (stdlib only)."""

from __future__ import annotations

import json
import platform
import ssl
import sys
import time
import urllib.error
import urllib.request
from typing import Any

try:
    from ..version import ADDON_VERSION as CLIENT_VERSION
except ImportError:
    CLIENT_VERSION = "1.1.1"
DEFAULT_BASE_URL = "https://api.motifect.io/api/v1"
DEFAULT_USER_AGENT = "MotifectMotion/1.0 (Motifect API Client)"
DEFAULT_POLL_INTERVAL = 3.0
DEFAULT_POLL_TIMEOUT = 600.0

MODEL_CHOICES = (
    ("motifect-v3-fast", "Motifect v3 Fast (8 credits)"),
    ("motifect-v3", "Motifect v3 (16 credits)"),
    ("kimodo-human", "Kimodo Human (20 credits)"),
)

MODEL_CREDITS = {
    "motifect-v3-fast": 8,
    "motifect-v3": 16,
    "kimodo-human": 20,
}

EXPORT_FORMATS = ("fbx", "bvh", "glb", "vrma")


class MotifectAPIError(Exception):
    """Raised when the API returns ok=false or an HTTP error."""

    def __init__(
        self,
        message: str,
        status: int | None = None,
        details: Any = None,
        diagnostics: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.status = status
        self.details = details
        self.diagnostics = diagnostics or {}


class MotifectClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        user_agent: str = DEFAULT_USER_AGENT,
    ):
        if not api_key or not api_key.strip():
            raise ValueError("API key is required")
        self.api_key = api_key.strip()
        self.base_url = base_url.rstrip("/")
        self.user_agent = user_agent
        self._ssl_context = ssl.create_default_context()
        self.last_diagnostics: dict[str, Any] = {}

    def _headers(self, json_body: bool = False) -> dict[str, str]:
        headers = {
            "X-API-Key": self.api_key,
            "Accept": "application/json",
            "User-Agent": self.user_agent,
        }
        if json_body:
            headers["Content-Type"] = "application/json"
        return headers

    @staticmethod
    def _mask_api_key(api_key: str) -> str:
        if len(api_key) <= 12:
            return "***"
        return f"{api_key[:8]}...{api_key[-4:]}"

    @staticmethod
    def format_work_status(work: dict) -> str:
        status = work.get("status", "unknown")
        progress = work.get("progress")
        if isinstance(progress, dict):
            message = progress.get("message") or progress.get("stage")
            if message:
                return f"{status}: {message}"
        elif isinstance(progress, (int, float)):
            pct = int(progress * 100) if progress <= 1 else int(progress)
            return f"{status} ({pct}%)"
        return status

    @staticmethod
    def _error_message(payload: dict, fallback: str) -> str:
        return (
            payload.get("error")
            or payload.get("detail")
            or payload.get("title")
            or fallback
        )

    @staticmethod
    def _parse_http_error(exc: urllib.error.HTTPError) -> tuple[str, dict | None, str]:
        raw = exc.read()
        text = raw.decode("utf-8", errors="replace").strip()
        payload = None
        if text:
            try:
                parsed = json.loads(text)
                if isinstance(parsed, dict):
                    payload = parsed
                    return MotifectClient._error_message(parsed, text), payload, text
            except json.JSONDecodeError:
                pass
            return f"HTTP {exc.code}: {text}", payload, text
        return str(exc), payload, text

    def _build_diagnostics(
        self,
        *,
        method: str,
        url: str,
        headers: dict[str, str],
        status: int | None = None,
        response_headers: dict[str, str] | None = None,
        response_body: str = "",
        error_type: str | None = None,
    ) -> dict[str, Any]:
        safe_headers = dict(headers)
        if "X-API-Key" in safe_headers:
            safe_headers["X-API-Key"] = self._mask_api_key(safe_headers["X-API-Key"])

        diagnostics = {
            "client_version": CLIENT_VERSION,
            "python_version": sys.version.replace("\n", " "),
            "platform": platform.platform(),
            "request": {
                "method": method,
                "url": url,
                "headers": safe_headers,
            },
            "response": {
                "status": status,
                "headers": response_headers or {},
                "body": response_body[:4000],
            },
            "error_type": error_type,
        }
        self.last_diagnostics = diagnostics
        return diagnostics

    def _ensure_online_access(self) -> None:
        try:
            from ..network import OnlineAccessDisabledError, ensure_online_access

            ensure_online_access()
        except OnlineAccessDisabledError as exc:
            raise MotifectAPIError(str(exc)) from exc

    def _request(
        self,
        method: str,
        path: str,
        body: dict | None = None,
        timeout: float = 60.0,
    ) -> dict:
        self._ensure_online_access()
        url = f"{self.base_url}{path}"
        data = None
        headers = self._headers(json_body=body is not None)
        if body is not None:
            data = json.dumps(body).encode("utf-8")

        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=self._ssl_context) as resp:
                raw = resp.read().decode("utf-8")
                payload = json.loads(raw)
                self._build_diagnostics(
                    method=method,
                    url=url,
                    headers=headers,
                    status=getattr(resp, "status", 200),
                    response_headers=dict(resp.headers.items()),
                    response_body=raw,
                )
        except urllib.error.HTTPError as exc:
            message, payload, text = self._parse_http_error(exc)
            diagnostics = self._build_diagnostics(
                method=method,
                url=url,
                headers=headers,
                status=exc.code,
                response_headers=dict(exc.headers.items()),
                response_body=text,
                error_type="http_error",
            )
            raise MotifectAPIError(
                message,
                status=exc.code,
                details=(payload or {}).get("details"),
                diagnostics=diagnostics,
            ) from exc
        except urllib.error.URLError as exc:
            diagnostics = self._build_diagnostics(
                method=method,
                url=url,
                headers=headers,
                response_body=str(exc.reason),
                error_type="url_error",
            )
            raise MotifectAPIError(
                f"Network error: {exc.reason}",
                diagnostics=diagnostics,
            ) from exc
        except json.JSONDecodeError as exc:
            diagnostics = self._build_diagnostics(
                method=method,
                url=url,
                headers=headers,
                response_body=raw if "raw" in locals() else "",
                error_type="json_decode_error",
            )
            raise MotifectAPIError(
                f"Invalid JSON response: {exc}",
                diagnostics=diagnostics,
            ) from exc

        if not payload.get("ok", False):
            diagnostics = self._build_diagnostics(
                method=method,
                url=url,
                headers=headers,
                status=200,
                response_body=json.dumps(payload),
                error_type="api_error",
            )
            raise MotifectAPIError(
                payload.get("error") or "Unknown API error",
                status=200,
                details=payload.get("details"),
                diagnostics=diagnostics,
            )
        return payload

    def diagnose(self, timeout: float = 30.0) -> dict[str, Any]:
        """Run a lightweight connectivity/auth check and return structured diagnostics."""
        self._ensure_online_access()
        report: dict[str, Any] = {
            "client_version": CLIENT_VERSION,
            "python_version": sys.version.replace("\n", " "),
            "platform": platform.platform(),
            "base_url": self.base_url,
            "user_agent_configured": self.user_agent,
            "api_key_masked": self._mask_api_key(self.api_key),
            "steps": [],
        }

        def add_step(name: str, **fields):
            report["steps"].append({"name": name, **fields})

        url = f"{self.base_url}/credits/balance"
        headers = self._headers(json_body=False)
        req = urllib.request.Request(url, headers=headers, method="GET")

        add_step(
            "request_prepared",
            method="GET",
            url=url,
            headers={
                key: (self._mask_api_key(value) if key == "X-API-Key" else value)
                for key, value in headers.items()
            },
            note="If User-Agent is missing here, Cloudflare will return error code 1010.",
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout, context=self._ssl_context) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                payload = json.loads(raw)
                add_step(
                    "http_response",
                    status=getattr(resp, "status", 200),
                    response_headers=dict(resp.headers.items()),
                    response_body=raw[:4000],
                )
                report["success"] = bool(payload.get("ok"))
                report["balance"] = payload.get("balance")
                report["last_diagnostics"] = self._build_diagnostics(
                    method="GET",
                    url=url,
                    headers=headers,
                    status=getattr(resp, "status", 200),
                    response_headers=dict(resp.headers.items()),
                    response_body=raw,
                )
                return report
        except urllib.error.HTTPError as exc:
            message, payload, text = self._parse_http_error(exc)
            add_step(
                "http_response",
                status=exc.code,
                response_headers=dict(exc.headers.items()),
                response_body=text,
                parsed_message=message,
                parsed_json=payload,
            )
            report["success"] = False
            report["error"] = message
            report["last_diagnostics"] = self._build_diagnostics(
                method="GET",
                url=url,
                headers=headers,
                status=exc.code,
                response_headers=dict(exc.headers.items()),
                response_body=text,
                error_type="http_error",
            )
            if text.strip() == "error code: 1010":
                report["likely_cause"] = (
                    "Cloudflare blocked the request (error 1010). "
                    "The User-Agent header is missing or still Python-urllib."
                )
            return report
        except Exception as exc:
            add_step("exception", error_type=type(exc).__name__, message=str(exc))
            report["success"] = False
            report["error"] = str(exc)
            return report

    @staticmethod
    def format_diagnostics(diagnostics: dict[str, Any]) -> str:
        return json.dumps(diagnostics, indent=2, ensure_ascii=False)

    def get_balance(self) -> dict:
        return self._request("GET", "/credits/balance")

    def generate(
        self,
        prompt: str,
        duration_seconds: int = 8,
        model_key: str = "motifect-v3",
        continue_from_work_id: str | None = None,
    ) -> dict:
        body: dict[str, Any] = {
            "prompt": prompt,
            "duration_seconds": duration_seconds,
            "model_key": model_key,
        }
        if continue_from_work_id:
            body["continue_from_work_id"] = continue_from_work_id
        return self._request("POST", "/motions/generate", body)

    def get_motion(self, work_id: str) -> dict:
        return self._request("GET", f"/motions/{work_id}")

    def convert(self, work_id: str, export_format: str = "fbx") -> dict:
        if export_format not in EXPORT_FORMATS:
            raise ValueError(f"Unsupported format: {export_format}")
        return self._request("POST", f"/motions/{work_id}/convert", {"format": export_format})

    def poll_until_complete(
        self,
        work_id: str,
        interval: float = DEFAULT_POLL_INTERVAL,
        timeout: float = DEFAULT_POLL_TIMEOUT,
        on_progress: callable | None = None,
    ) -> dict:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            payload = self.get_motion(work_id)
            work = payload["item"]
            status = work.get("status")
            if on_progress:
                on_progress(work)
            if status == "completed":
                return work
            if status == "failed":
                summary = work.get("error_summary") or "Motion generation failed"
                raise MotifectAPIError(summary)
            time.sleep(interval)
        raise MotifectAPIError(f"Timed out waiting for work {work_id}")

    @staticmethod
    def find_asset_url(work: dict, export_format: str, asset_role: str | None = None) -> str | None:
        for asset in work.get("assets") or []:
            if asset.get("format") != export_format:
                continue
            if asset_role and asset.get("asset_role") != asset_role:
                continue
            url = asset.get("url")
            if url:
                return url
        return None

    def download(self, url: str, dest_path: str, timeout: float = 120.0) -> str:
        self._ensure_online_access()
        headers = {"User-Agent": self.user_agent, "Accept": "*/*"}
        req = urllib.request.Request(url, method="GET", headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=self._ssl_context) as resp:
                data = resp.read()
        except urllib.error.HTTPError as exc:
            message, _, text = self._parse_http_error(exc)
            diagnostics = self._build_diagnostics(
                method="GET",
                url=url,
                headers=headers,
                status=exc.code,
                response_headers=dict(exc.headers.items()),
                response_body=text,
                error_type="download_http_error",
            )
            raise MotifectAPIError(message, status=exc.code, diagnostics=diagnostics) from exc
        except urllib.error.URLError as exc:
            raise MotifectAPIError(f"Download failed: {exc.reason}") from exc

        with open(dest_path, "wb") as handle:
            handle.write(data)
        return dest_path

    def generate_and_export(
        self,
        prompt: str,
        dest_path: str,
        export_format: str = "fbx",
        duration_seconds: int = 8,
        model_key: str = "motifect-v3",
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        poll_timeout: float = DEFAULT_POLL_TIMEOUT,
        on_progress: callable | None = None,
    ) -> dict:
        gen = self.generate(prompt, duration_seconds, model_key)
        work_id = gen["data"]["work"]["id"]

        work = self.poll_until_complete(work_id, poll_interval, poll_timeout, on_progress)

        url = self.find_asset_url(work, export_format, asset_role="export_file")
        if not url:
            convert_payload = self.convert(work_id, export_format)
            work = convert_payload["item"]
            url = self.find_asset_url(work, export_format, asset_role="export_file")

        if not url:
            raise MotifectAPIError(f"No {export_format.upper()} export found for work {work_id}")

        self.download(url, dest_path)
        return work
