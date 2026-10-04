import io
import json
import time
import zipfile

import pytest
from fastapi.testclient import TestClient
from PIL import Image


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    import os

    tmp = tmp_path_factory.mktemp("api")
    os.environ.update({
        "DATABASE_URL": f"sqlite:///{tmp / 'test.db'}", "STORAGE_DIR": str(tmp / "storage"),
        "TRIPO_MODE": "mock", "MOCK_TASK_SECONDS": "0", "QUEUE_BACKEND": "inline",
        "PIPELINE_INTERNAL_PX": "256", "PIPELINE_PREVIEW_PX": "128", "TRIPO_API_KEY": "",
        "GENERATION_LIMIT_MOCK": "3", "GLOBAL_DAILY_GENERATION_CAP": "100",
        "REGISTRATION_REQUIRES_INVITE": "false", "SECRET_KEY": "test-secret-key-0123456789",
    })
    from biotile_api import models, settings, storage

    settings.get_settings.cache_clear()
    models.reset_engine()
    storage.reset_storage()
    from biotile_api.main import app

    with TestClient(app) as c:
        r = c.post("/api/auth/register", json={"name": "Test School", "email": "teacher@example.org",
                                               "password": "correct horse battery", "type": "school"})
        assert r.status_code == 200, r.text
        yield c


def _wait(client, job_id, timeout=120):
    t0 = time.time()
    while time.time() - t0 < timeout:
        j = client.get(f"/api/jobs/{job_id}").json()
        if j["status"] in ("success", "failed"):
            return j
        time.sleep(0.1)
    raise TimeoutError(job_id)


def _png(w=300, h=300):
    buf = io.BytesIO()
    Image.new("RGB", (w, h), (120, 110, 90)).save(buf, format="PNG")
    return buf.getvalue()


def test_full_photo_flow(client):
    r = client.post("/api/uploads", files={"file": ("rock.png", _png(), "image/png")})
    assert r.status_code == 200, r.text
    up = r.json()
    d = client.post("/api/designs", json={"title": "Test rock", "source_type": "photo",
                                          "upload_id": up["upload_id"]}).json()
    job = client.post(f"/api/designs/{d['id']}/generate").json()
    j = _wait(client, job["job_id"])
    assert j["status"] == "success", j

    prev = client.get(f"/api/designs/{d['id']}/preview").json()
    assert prev["front"]["ny"] == 192 and prev["code"].startswith("BT-") and {
        c["id"] for c in prev["checks"]} >= {"periodicity", "draft",
                                                                       "min_thickness", "bed_fit"}
    r = client.patch(f"/api/designs/{d['id']}/params",
                     json={"macro_depth_mm": 12, "functional": {"nest_spacing_mm": 30.0}})
    assert r.status_code == 200, r.text
    assert r.json()["params"]["functional"]["nest_spacing_mm"] == 30.0
    hexr = client.patch(f"/api/designs/{d['id']}/params", json={"shape": "hex"})
    assert hexr.status_code == 200 and hexr.json()["shape"] == "hex"
    client.patch(f"/api/designs/{d['id']}/params", json={"shape": "square"})
    bad = client.patch(f"/api/designs/{d['id']}/params", json={"functional": {
        "channel_count": 7}})
    assert bad.status_code == 422

    j = _wait(client, client.post(f"/api/designs/{d['id']}/export").json()["job_id"])
    assert j["status"] == "success", j
    full = client.get(f"/api/designs/{d['id']}").json()
    assert full["code"].startswith("BT-") and full["has_package"]
    assert full["model_seed"] and full["tripo_model_version"] == "v3.1-20260211"

    z = zipfile.ZipFile(io.BytesIO(client.get(f"/api/designs/{d['id']}/package").content))
    names = set(z.namelist())
    assert {"design.json", "stl/matrix.stl", "stl/frame_top.stl", "stl/backplate.stl",
            "stl/hole_punch.stl",
            "docs/instructions.pdf", "heightfield/front_16bit.png"} <= names
    meta = json.loads(z.read("design.json"))
    assert meta["params"]["macro_depth_mm"] == 12 and meta["pipeline_version"]

    assert client.get(f"/api/designs/{d['id']}/package").status_code == 200
    assert client.post(f"/api/designs/{d['id']}/publish",
                       json={"license_confirmed": False}).status_code == 422
    assert client.post(f"/api/designs/{d['id']}/publish",
                       json={"license_confirmed": True}).status_code == 200
    gallery = client.get("/api/designs").json()
    assert any(g["id"] == d["id"] for g in gallery)
    assert client.get(full["preview_url"]).status_code == 200

    inst = client.post("/api/instances", json={
        "design_id": d["id"], "material": "clay", "process": "press_mould",
        "orientation_deg": 0, "booster": True, "installed_date": "2026-10-04",
        "mounting_adapter": "wall", "mounting_detail": "Schulhofmauer Nord",
        "geo_lat": 48.7758123, "geo_lon": 9.1829321, "geo_visibility": "exact"}).json()
    assert inst["id"] == full["code"] + "-001"
    assert inst["geo"]["precision"] == "exact"  # owner sees it exactly
    second = client.post("/api/instances", json={
        "design_id": d["id"], "material": "concrete", "process": "matrix_down",
        "orientation_deg": 180}).json()
    assert second["id"] == full["code"] + "-002"
    found = client.get(f"/api/lookup/{full['code'].lower()}").json()
    assert found["kind"] == "design" and [i["id"] for i in found["instances"]] == [
        inst["id"], second["id"]]
    assert client.get(f"/api/lookup/{inst['id']}").json()["kind"] == "instance"
    assert client.post("/api/instances", json={
        "design_id": d["id"], "material": "clay", "process": "press_mould"}).status_code == 422
    card = client.get(f"/api/instances/{inst['id']}/reference-card.pdf")
    assert card.content[:4] == b"%PDF"
    r = client.post(f"/api/instances/{inst['id']}/observations",
                    data={"observed_at": "2026-11-04", "observer_role": "student_group",
                          "species": json.dumps([{"name": "Grimmia pulvinata", "group": "moss",
                                                  "certainty": "likely"}])},
                    files={"photo": ("o.png", _png(), "image/png")})
    assert r.status_code == 200, r.text
    obs = r.json()["observations"]
    assert obs[0]["species"][0]["group"] == "moss" and obs[0]["photo_url"]

    child = client.post(f"/api/designs/{d['id']}/remix").json()
    assert child["parent_design_id"] == d["id"] and child["lineage"][0]["id"] == d["id"]


def test_procedural_reference_tile(client):
    d = client.post("/api/designs", json={"title": "REF-GEO", "source_type": "procedural",
                                          "surface_type": "REF-GEO"}).json()
    j = _wait(client, client.post(f"/api/designs/{d['id']}/generate").json()["job_id"])
    assert j["status"] == "success", j
    prev = client.get(f"/api/designs/{d['id']}/preview").json()
    assert prev["params"]["functional"]["template"] == "none"


def test_library_sample_in_mock_mode(client):
    d = client.post("/api/designs", json={"title": "Tafoni", "source_type": "procedural",
                                          "surface_type": "tafoni"}).json()
    j = _wait(client, client.post(f"/api/designs/{d['id']}/generate").json()["job_id"])
    assert j["status"] == "success", j


def test_source_photos_are_not_public(client):
    up = client.post("/api/uploads", files={"file": ("p.png", _png(), "image/png")}).json()
    assert client.get(f"/api/files/uploads/xx/{up['upload_id']}.png").status_code == 404


def test_upload_rejects_wrong_type(client):
    r = client.post("/api/uploads", files={"file": ("a.gif", b"GIF89a", "image/gif")})
    assert r.status_code == 415


def test_config_never_leaks_key(client):
    cfg = client.get("/api/config").json()
    assert "tripo_api_key" not in json.dumps(cfg)


def test_requires_login():
    from biotile_api.main import app

    with TestClient(app) as anon:
        assert anon.post("/api/uploads", files={"file": ("a.png", _png(), "image/png")}).status_code == 401
        assert anon.post("/api/designs", json={"title": "x", "source_type": "procedural",
                                              "surface_type": "REF-GEO"}).status_code == 401
        assert anon.get("/api/auth/me").json() is None


def test_login_logout_and_wrong_password(client):
    from biotile_api.main import app

    with TestClient(app) as c2:
        assert c2.post("/api/auth/login", json={"email": "teacher@example.org",
                                                "password": "wrong password!"}).status_code == 401
        r = c2.post("/api/auth/login", json={"email": "TEACHER@example.org",
                                             "password": "correct horse battery"})
        assert r.status_code == 200 and r.json()["quota"]["mode"] == "mock"
        assert c2.get("/api/auth/me").json()["email"] == "teacher@example.org"
        c2.post("/api/auth/logout")
        assert c2.get("/api/auth/me").json() is None


def test_generation_limit_cannot_be_exceeded(client):
    """Limit is 3 (env). Reference tiles are free; every Tripo generation is charged."""
    used = client.get("/api/auth/me").json()["quota"]["used"]
    codes = []
    for _ in range(3 - used + 2):
        d = client.post("/api/designs", json={"title": "Bark", "source_type": "procedural",
                                              "surface_type": "bark"}).json()
        codes.append(client.post(f"/api/designs/{d['id']}/generate").status_code)
    assert codes.count(200) == 3 - used and codes[-1] == 429
    me = client.get("/api/auth/me").json()["quota"]
    assert me["used"] == me["limit"] == 3 and me["remaining"] == 0
    ref = client.post("/api/designs", json={"title": "REF", "source_type": "procedural",
                                            "surface_type": "REF-FLAT"}).json()
    assert client.post(f"/api/designs/{ref['id']}/generate").status_code == 200  # free


def test_other_accounts_cannot_touch_drafts(client):
    from biotile_api.main import app

    d = client.post("/api/designs", json={"title": "Mine", "source_type": "procedural",
                                          "surface_type": "REF-FLAT"}).json()
    with TestClient(app) as other:
        other.post("/api/auth/register", json={"name": "Other", "email": "other@example.org",
                                               "password": "another long password"})
        assert other.get(f"/api/designs/{d['id']}").status_code == 404
        assert other.post(f"/api/designs/{d['id']}/generate").status_code == 403
        assert all(x["id"] != d["id"] for x in other.get("/api/designs?status=all").json())


def test_school_positions_are_rounded_for_others(client):
    from biotile_api.main import app

    d = client.post("/api/designs", json={"title": "REF", "source_type": "procedural",
                                          "surface_type": "REF-GEO"}).json()
    assert client.post(f"/api/designs/{d['id']}/generate").status_code == 200
    _wait(client, client.get(f"/api/designs/{d['id']}/job?kind=generate").json()["id"])
    inst = client.post("/api/instances", json={
        "design_id": d["id"], "material": "clay", "process": "press_mould", "orientation_deg": 0,
        "geo_lat": 48.7758123, "geo_lon": 9.1829321, "geo_visibility": "exact"}).json()
    # the test account is a school: exact is downgraded to approx for everyone else
    with TestClient(app) as anon:
        pub = anon.get(f"/api/instances/{inst['id']}").json()
    assert pub["geo"] == {"lat": 48.776, "lon": 9.183, "precision": "approx"}


def test_registration_needs_valid_invite(tmp_path):
    import os

    from biotile_api import auth as auth_mod
    from biotile_api import settings
    from biotile_api.main import app
    from biotile_api.models import Invite, SessionLocal

    os.environ["REGISTRATION_REQUIRES_INVITE"] = "true"
    settings.get_settings.cache_clear()
    try:
        code = auth_mod.generate_invite_code()
        with SessionLocal() as db:
            db.add(Invite(code_hash=auth_mod.hash_invite(code), note="test", max_uses=1))
            db.commit()
            stored = db.query(Invite).filter_by(note="test").one().code_hash
        assert code.replace("-", "") not in stored  # only the HMAC is stored
        body = {"name": "School B", "email": "b@example.org", "password": "long enough password"}
        with TestClient(app) as c:
            assert c.post("/api/auth/register", json={**body, "invite_code": "WRONG-CODE"}).status_code == 403
            assert c.post("/api/auth/register", json={**body, "invite_code": code.lower()}).status_code == 200
        with TestClient(app) as c:
            again = {**body, "email": "c@example.org", "invite_code": code}
            assert c.post("/api/auth/register", json=again).status_code == 403  # used up
        assert app.openapi() and "invite" not in str(TestClient(app).get("/api/config").json()).replace(
            "invite_required", "")
    finally:
        os.environ["REGISTRATION_REQUIRES_INVITE"] = "false"
        settings.get_settings.cache_clear()


def test_jury_login_and_locations():
    from biotile_api.main import app

    with TestClient(app) as c:
        me = c.post("/api/auth/jury").json()
        assert me["type"] == "jury" and me["quota"]["mode"] == "mock"  # jury cap is live-only
        assert c.get("/api/auth/me").json()["name"] == "Jury"
        assert isinstance(c.get("/api/locations").json(), list)
        assert "tripo_api_key" not in c.get("/api/config").text


def test_live_quota_falls_back_to_mock():
    from biotile_api import auth
    from biotile_api.main import app
    from biotile_api.models import Account, SessionLocal

    with TestClient(app) as c:
        c.post("/api/auth/jury")
        with SessionLocal() as db:
            acc = db.query(Account).filter(Account.type == "jury").one()
            acc.generations_used_live = acc.generation_limit  # live quota used up
            db.commit()
            assert auth.quota(acc, "live")["remaining"] == 0
            before = acc.generations_used_mock
            assert auth.charge_with_fallback(db, acc, "live") == "mock"
            assert acc.generations_used_mock == before + 1
