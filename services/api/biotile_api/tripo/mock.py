"""MockTripoClient (replay) and RecordingTripoClient (record) - no credits in dev and tests.

Fixture layout (tests/fixtures/tripo/):
    synthetic_index.json, synthetic_*.glb      procedural stand-ins (scripts/make_mock_fixtures.py)
    recorded/<sha256-of-image>/                live responses captured with TRIPO_RECORD=1
        request.json  task.json  model.glb  [rendered.png]

Replay: an uploaded image whose SHA-256 has a recording replays exactly that recording;
any other image deterministically maps to one of the synthetic fixtures (a "hint" such as the
library surface type can pick one explicitly). Task progress is simulated from the elapsed
time encoded in the task id, so the mock is stateless across API and worker processes.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

from .client import TaskInfo, TripoClient, TripoError, redact

MOCK_SCHEME = "mock://"


class MockTripoClient(TripoClient):
    mode = "mock"

    def __init__(self, fixtures_dir: Path, task_seconds: float = 4.0):
        self.dir = Path(fixtures_dir)
        self.task_seconds = task_seconds
        idx = self.dir / "synthetic_index.json"
        self.synthetic = json.loads(idx.read_text()) if idx.exists() else {}
        if not self.synthetic and not (self.dir / "recorded").exists():
            raise FileNotFoundError(f"no Tripo fixtures in {self.dir}")

    # -- helpers ------------------------------------------------------------------------
    def _fixture_for(self, sha: str, hint: str | None) -> str:
        rec = self.dir / "recorded" / sha / "model.glb"
        if rec.exists():
            return str(rec.relative_to(self.dir))
        if hint and hint in self.synthetic:
            return self.synthetic[hint]["model"]
        names = sorted(self.synthetic)
        return self.synthetic[names[int(sha[:8], 16) % len(names)]]["model"]

    # -- interface ----------------------------------------------------------------------
    def upload_file(self, data: bytes, filename: str, content_type: str) -> str:
        if len(data) > 20 * 1024 * 1024:
            raise TripoError(1004, "file too large (max 20 MB)")
        return "file_mock_" + hashlib.sha256(data).hexdigest()

    def image_to_model(self, request: dict, hint: str | None = None) -> str:
        token = str(request.get("input", ""))
        if not token.startswith("file_mock_"):
            raise TripoError(1004, "unknown file token")
        sha = token.removeprefix("file_mock_")
        fixture = self._fixture_for(sha, hint)
        created_ms = int(time.time() * 1000)
        # task id carries everything needed to answer get_task without server state
        return f"mock-{created_ms}-{fixture}"

    def get_task(self, task_id: str) -> TaskInfo:
        try:
            _, created_ms, fixture = task_id.split("-", 2)
            created = int(created_ms) / 1000.0
        except ValueError:
            raise TripoError(2001, f"task {task_id} not found")
        elapsed = time.time() - created
        if self.task_seconds <= 0 or elapsed >= self.task_seconds:
            status, progress = "success", 100
        elif elapsed < 0.15 * self.task_seconds:
            status, progress = "queued", 0
        else:
            status, progress = "running", int(100 * elapsed / self.task_seconds)
        data = {"task_id": task_id, "type": "image_to_model", "status": status,
                "progress": progress, "credits_consumed": 0.0}
        if status == "success":
            data["output"] = {"model_url": MOCK_SCHEME + fixture, "rendered_image_url": None}
        return TaskInfo.from_response(data)

    def download(self, url: str) -> bytes:
        if not url.startswith(MOCK_SCHEME):
            raise TripoError(-1, f"mock client cannot download {url}")
        path = (self.dir / url.removeprefix(MOCK_SCHEME)).resolve()
        if self.dir.resolve() not in path.parents:
            raise TripoError(-1, "fixture path escapes fixture dir")
        return path.read_bytes()

    def balance(self) -> dict:
        return {"balance": None, "frozen": None, "mode": "mock"}


class RecordingTripoClient(TripoClient):
    """Wraps the live client and stores every image-to-model round trip as a fixture."""

    mode = "live+record"

    def __init__(self, inner: TripoClient, fixtures_dir: Path):
        self.inner = inner
        self.dir = Path(fixtures_dir) / "recorded"
        self._token_sha: dict[str, str] = {}
        self._task_sha: dict[str, str] = {}

    def upload_file(self, data: bytes, filename: str, content_type: str) -> str:
        token = self.inner.upload_file(data, filename, content_type)
        sha = hashlib.sha256(data).hexdigest()
        self._token_sha[token] = sha
        d = self.dir / sha
        d.mkdir(parents=True, exist_ok=True)
        ext = Path(filename).suffix or ".bin"
        (d / f"input{ext}").write_bytes(data)
        return token

    def image_to_model(self, request: dict) -> str:
        task_id = self.inner.image_to_model(request)
        sha = self._token_sha.get(str(request.get("input")))
        if sha:
            self._task_sha[task_id] = sha
            (self.dir / sha / "request.json").write_text(
                json.dumps(redact(request), indent=2, sort_keys=True) + "\n")
        return task_id

    def get_task(self, task_id: str) -> TaskInfo:
        info = self.inner.get_task(task_id)
        sha = self._task_sha.get(task_id)
        if sha and info.done:
            (self.dir / sha / "task.json").write_text(
                json.dumps(redact(info.raw), indent=2, sort_keys=True) + "\n")
        return info

    def download(self, url: str) -> bytes:
        data = self.inner.download(url)
        for task_id, sha in self._task_sha.items():
            task_file = self.dir / sha / "task.json"
            if task_file.exists() and url in task_file.read_text():
                name = "model.glb" if data[:4] == b"glTF" else "rendered.png"
                (self.dir / sha / name).write_bytes(data)
        return data

    def balance(self) -> dict:
        return self.inner.balance()


def make_client(mode: str, api_key: str | None, fixtures_dir: Path, record: bool = False,
                base_url: str | None = None, mock_task_seconds: float = 4.0) -> TripoClient:
    from .client import DEFAULT_BASE_URL, LiveTripoClient

    if mode == "mock":
        return MockTripoClient(fixtures_dir, task_seconds=mock_task_seconds)
    if mode == "live":
        live = LiveTripoClient(api_key or "", base_url or DEFAULT_BASE_URL)
        return RecordingTripoClient(live, fixtures_dir) if record else live
    raise ValueError("TRIPO_MODE must be 'mock' or 'live'")
