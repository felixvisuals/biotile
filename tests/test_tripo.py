import json

import httpx
import pytest
from biotile_api.tripo import (
    MockTripoClient,
    RecordingTripoClient,
    TripoError,
    image_to_model_request,
    poll_until_done,
)
from biotile_api.tripo.client import LiveTripoClient
from conftest import FIXTURES


def test_standard_request_matches_brief():
    req = image_to_model_request("file_abc123", 1234567, 1234567)
    assert req == {
        "input": "file_abc123", "model": "v3.1-20260211", "texture": True, "pbr": True,
        "texture_version": "v3.5-20260815", "texture_quality": "extreme", "delight": True,
        "texture_alignment": "geometry", "geometry_quality": "detailed", "face_limit": 1000000,
        "model_seed": 1234567, "texture_seed": 1234567, "enable_image_autofix": False,
        "export_uv": True,
    }
    for forbidden in ("export_orientation", "compress", "quad", "generate_parts", "auto_size"):
        assert forbidden not in req


def test_mock_full_flow_is_deterministic():
    c = MockTripoClient(FIXTURES, task_seconds=0)
    t1 = c.upload_file(b"same image", "a.png", "image/png")
    t2 = c.upload_file(b"same image", "b.png", "image/png")
    assert t1 == t2
    task = c.image_to_model(image_to_model_request(t1, 1, 1))
    info = poll_until_done(c, task, sleep=lambda s: None)
    assert info.status == "success" and info.model_url.startswith("mock://")
    assert c.download(info.model_url)[:4] == b"glTF"


def test_mock_hint_selects_fixture():
    c = MockTripoClient(FIXTURES, task_seconds=0)
    tok = c.upload_file(b"x", "x.png", "image/png")
    info = c.get_task(c.image_to_model(image_to_model_request(tok, 1, 1), hint="tafoni"))
    assert info.model_url.endswith("synthetic_tafoni.glb")


def test_mock_progress_simulation():
    c = MockTripoClient(FIXTURES, task_seconds=1000)
    tok = c.upload_file(b"y", "y.png", "image/png")
    info = c.get_task(c.image_to_model(image_to_model_request(tok, 1, 1)))
    assert info.status in ("queued", "running") and not info.done


def test_mock_download_cannot_escape_fixture_dir():
    c = MockTripoClient(FIXTURES)
    with pytest.raises(TripoError):
        c.download("mock://../../pyproject.toml")


def _live(handler):
    return LiveTripoClient("test-key", transport=httpx.MockTransport(handler))


def test_live_client_sends_bearer_and_parses():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers["authorization"]
        seen["path"] = request.url.path
        if request.url.path.endswith("/files"):
            assert b'name="file"' in request.content
            return httpx.Response(200, json={"code": 0, "data": {"file_token": "file_1"}})
        if request.url.path.endswith("/generation/image-to-model"):
            body = json.loads(request.content)
            assert body["input"] == "file_1"
            return httpx.Response(200, json={"code": 0, "data": {"task_id": "t1"}})
        return httpx.Response(200, json={"code": 0, "data": {
            "task_id": "t1", "status": "success", "progress": 100, "credits_consumed": 30.0,
            "output": {"model_url": "https://x/m.glb", "rendered_image_url": "https://x/r.png"}}})

    c = _live(handler)
    assert c.upload_file(b"img", "a.png", "image/png") == "file_1"
    assert seen["auth"] == "Bearer test-key" and seen["path"] == "/v3/files"
    assert c.image_to_model(image_to_model_request("file_1", 1, 2)) == "t1"
    info = c.get_task("t1")
    assert info.done and info.model_url == "https://x/m.glb" and info.credits_consumed == 30.0


@pytest.mark.parametrize("code,key", [(2010, "errors.tripo_insufficient_credits"),
                                      (1004, "errors.tripo_invalid_params")])
def test_live_client_error_codes(code, key):
    c = _live(lambda r: httpx.Response(400, json={"code": code, "message": "m",
                                                  "suggestion": "s"}))
    with pytest.raises(TripoError) as e:
        c.image_to_model({"input": "x"})
    assert e.value.code == code and e.value.user_message_key == key


def test_live_client_requires_key():
    with pytest.raises(ValueError):
        LiveTripoClient("")


def test_polling_backoff_and_timeout():
    class Never(MockTripoClient):
        def get_task(self, task_id):
            from biotile_api.tripo import TaskInfo
            return TaskInfo(task_id=task_id, status="running", progress=50)

    delays, now = [], [0.0]

    def sleep(s):
        delays.append(s)
        now[0] += s

    with pytest.raises(TimeoutError):
        poll_until_done(Never(FIXTURES), "t", sleep=sleep, clock=lambda: now[0])
    assert delays[0] == 2.0 and max(delays) == 15.0 and sum(delays) <= 600.0


def test_recording_client_writes_fixture(tmp_path):
    src = MockTripoClient(FIXTURES, task_seconds=0)
    rec = RecordingTripoClient(src, tmp_path)
    tok = rec.upload_file(b"photo-bytes", "p.jpg", "image/jpeg")
    task = rec.image_to_model(image_to_model_request(tok, 5, 6))
    info = poll_until_done(rec, task, sleep=lambda s: None)
    rec.download(info.model_url)
    d = next((tmp_path / "recorded").iterdir())
    assert {p.name for p in d.iterdir()} >= {"input.jpg", "request.json", "task.json",
                                             "model.glb"}
    # A mock pointed at the recording replays it for the same image.
    replay = MockTripoClient(tmp_path, task_seconds=0)
    tok2 = replay.upload_file(b"photo-bytes", "p.jpg", "image/jpeg")
    info2 = replay.get_task(replay.image_to_model(image_to_model_request(tok2, 5, 6)))
    assert "recorded/" in info2.model_url
