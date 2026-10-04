"""Tripo API v3 client: interface, live implementation, request builder, polling.

Only parameters documented in docs/PROJECT_BRIEF.de.md section 7 are used.
Verified against https://developers.tripo3d.ai/en/docs (2026-10-03):
  * POST /v3/files: multipart/form-data, field "file"; response data.file_token;
    images JPEG/PNG max 20 MB.
  * GET /v3/tasks/{task_id}: data.status queued|running|success|failed|cancelled,
    data.progress 0-100, data.output.model_url / rendered_image_url (only on success),
    data.error_code / error_message (only on failure), data.credits_consumed.
Still to confirm on the first live run (docs page did not render for us):
  * the exact image-to-model field set (taken verbatim from brief 7.3), and whether
    /v3/files accepts WebP (the brief allows it client-side; we convert WebP to PNG).
The API key never leaves this module: it is not logged, not stored, not returned.
"""

from __future__ import annotations

import abc
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import httpx

log = logging.getLogger("biotile.tripo")

DEFAULT_BASE_URL = "https://openapi.tripo3d.ai/v3"
MODEL_VERSION = "v3.1-20260211"
TEXTURE_VERSION = "v3.5-20260815"
TERMINAL = {"success", "failed", "cancelled"}

# Error codes with dedicated handling (brief 7.5)
ERR_INSUFFICIENT_CREDITS = 2010
ERR_INVALID_PARAM_COMBINATION = 1004


class TripoError(Exception):
    def __init__(self, code: int, message: str, suggestion: str | None = None,
                 raw: dict | None = None):
        super().__init__(f"Tripo error {code}: {message}")
        self.code = code
        self.message = message
        self.suggestion = suggestion
        self.raw = raw or {}

    @property
    def user_message_key(self) -> str:
        if self.code == ERR_INSUFFICIENT_CREDITS:
            return "errors.tripo_insufficient_credits"
        if self.code == ERR_INVALID_PARAM_COMBINATION:
            return "errors.tripo_invalid_params"
        return "errors.tripo_generic"


@dataclass
class TaskInfo:
    task_id: str
    status: str
    progress: int = 0
    model_url: str | None = None
    rendered_image_url: str | None = None
    credits_consumed: float | None = None
    error_code: int | None = None
    error_message: str | None = None
    raw: dict = field(default_factory=dict)

    @property
    def done(self) -> bool:
        return self.status in TERMINAL

    @classmethod
    def from_response(cls, data: dict) -> "TaskInfo":
        out = data.get("output") or {}
        return cls(task_id=data.get("task_id", ""), status=data.get("status", "queued"),
                   progress=int(data.get("progress") or 0), model_url=out.get("model_url"),
                   rendered_image_url=out.get("rendered_image_url"),
                   credits_consumed=data.get("credits_consumed"),
                   error_code=data.get("error_code"), error_message=data.get("error_message"),
                   raw=data)


def image_to_model_request(file_token: str, model_seed: int, texture_seed: int,
                           enable_image_autofix: bool = False,
                           face_limit: int = 1_000_000) -> dict:
    """Standard request, brief 7.3. Deliberately NOT set: export_orientation, compress, quad,
    generate_parts, auto_size (see brief for reasons)."""
    return {
        "input": file_token,
        "model": MODEL_VERSION,
        "texture": True,
        "pbr": True,  # normal map carries the micro structure (v1: micro band)
        "texture_version": TEXTURE_VERSION,  # delight only works with this texture model
        "texture_quality": "extreme",
        "delight": True,  # removes baked light: cast shadows would become fake geometry
        "texture_alignment": "geometry",
        "geometry_quality": "detailed",
        "face_limit": face_limit,
        "model_seed": int(model_seed),
        "texture_seed": int(texture_seed),
        "enable_image_autofix": bool(enable_image_autofix),  # off: no invented detail
        "export_uv": True,
    }


class TripoClient(abc.ABC):
    """Interface shared by LiveTripoClient and MockTripoClient."""

    mode: str = "abstract"

    @abc.abstractmethod
    def upload_file(self, data: bytes, filename: str, content_type: str) -> str: ...

    @abc.abstractmethod
    def image_to_model(self, request: dict) -> str: ...

    @abc.abstractmethod
    def get_task(self, task_id: str) -> TaskInfo: ...

    @abc.abstractmethod
    def download(self, url: str) -> bytes: ...

    @abc.abstractmethod
    def balance(self) -> dict: ...


class LiveTripoClient(TripoClient):
    mode = "live"

    def __init__(self, api_key: str, base_url: str = DEFAULT_BASE_URL, timeout: float = 60.0,
                 transport: httpx.BaseTransport | None = None):
        if not api_key:
            raise ValueError("TRIPO_API_KEY is not set (required for TRIPO_MODE=live)")
        self._http = httpx.Client(base_url=base_url.rstrip("/"), timeout=timeout,
                                  headers={"Authorization": f"Bearer {api_key}"},
                                  transport=transport)

    def _unwrap(self, resp: httpx.Response) -> dict:
        try:
            body = resp.json()
        except ValueError:
            raise TripoError(resp.status_code, f"non-JSON response (HTTP {resp.status_code})")
        if body.get("code", -1) != 0:
            raise TripoError(int(body.get("code", resp.status_code)), body.get("message", ""),
                             body.get("suggestion"), raw=body)
        return body.get("data") or {}

    def upload_file(self, data: bytes, filename: str, content_type: str) -> str:
        resp = self._http.post("/files", files={"file": (filename, data, content_type)})
        token = self._unwrap(resp).get("file_token")
        if not token:
            raise TripoError(-1, "upload response without file_token")
        return token

    def image_to_model(self, request: dict) -> str:
        data = self._unwrap(self._http.post("/generation/image-to-model", json=request))
        task_id = data.get("task_id")
        if not task_id:
            raise TripoError(-1, "generation response without task_id", raw=data)
        return task_id

    def get_task(self, task_id: str) -> TaskInfo:
        return TaskInfo.from_response(self._unwrap(self._http.get(f"/tasks/{task_id}")))

    def download(self, url: str) -> bytes:
        # Result URLs are pre-signed; do not send the API key to a foreign host.
        with httpx.Client(timeout=120.0, follow_redirects=True) as c:
            r = c.get(url)
            r.raise_for_status()
            return r.content

    def balance(self) -> dict:
        return self._unwrap(self._http.get("/account/balance"))


def poll_until_done(client: TripoClient, task_id: str, timeout_s: float = 600.0,
                    start_s: float = 2.0, cap_s: float = 15.0,
                    on_progress: Callable[[TaskInfo], None] | None = None,
                    sleep: Callable[[float], None] = time.sleep,
                    clock: Callable[[], float] = time.monotonic) -> TaskInfo:
    """Exponential backoff polling: start 2 s, cap 15 s, timeout 10 min (brief 7.5)."""
    t0 = clock()
    delay = start_s
    while True:
        info = client.get_task(task_id)
        if on_progress:
            on_progress(info)
        if info.done:
            return info
        if clock() - t0 + delay > timeout_s:
            raise TimeoutError(f"Tripo task {task_id} not finished after {timeout_s:.0f} s")
        sleep(delay)
        delay = min(cap_s, delay * 1.6)


def redact(obj: Any) -> Any:
    """Drop anything that looks like a credential before persisting requests/responses."""
    if isinstance(obj, dict):
        return {k: ("***" if k.lower() in {"authorization", "api_key", "key", "token"} else
                    redact(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [redact(v) for v in obj]
    return obj
