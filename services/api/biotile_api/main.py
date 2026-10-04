"""BIOTILE REST API (brief 12.2). Run: uvicorn biotile_api.main:app --reload"""

from __future__ import annotations

import hashlib
import io
import json
import logging
import re
from contextlib import asynccontextmanager
from datetime import date

from biotile_geometry import constants as C
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import auth
from . import design_service as svc
from .auth import current_account, get_db, optional_account
from .models import Account, Design, Instance, Job, Observation, SessionLocal, Upload, init_db
from .queue import enqueue
from .settings import get_settings
from .storage import get_storage

log = logging.getLogger("biotile.api")
ALLOWED_IMAGE_TYPES = {"image/png": "PNG", "image/jpeg": "JPEG", "image/webp": "WEBP"}


def demo_account(db: Session) -> Account:
    acc = db.scalar(select(Account).where(Account.name == get_settings().demo_account_name))
    if acc is None:
        acc = Account(name=get_settings().demo_account_name, type="project",
                      region_coarse="Stuttgart", credit_quota=500.0)
        db.add(acc)
        db.commit()
    return acc


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    with SessionLocal() as db:
        demo_account(db)
    yield


app = FastAPI(title="BIOTILE API", version=C.PIPELINE_VERSION, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=get_settings().cors_origins.split(","),
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


def _owns(d: Design, acc: Account | None) -> bool:
    return acc is not None and d.author_account_id == acc.id


def _require_owner(d: Design, acc: Account) -> None:
    if not _owns(d, acc):
        raise HTTPException(403, detail={"key": "errors.not_yours"})


def _visible(d: Design, acc: Account | None) -> bool:
    return d.status == "published" or _owns(d, acc)


# -- accounts -------------------------------------------------------------------------
class RegisterBody(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=10, max_length=200)
    type: str = Field("school", pattern="^(school|project|researcher)$")
    region_coarse: str | None = Field(None, max_length=200)
    invite_code: str | None = None


class LoginBody(BaseModel):
    email: EmailStr
    password: str = Field(max_length=200)


def _me(acc: Account) -> dict:
    mode = get_settings().tripo_mode
    q = auth.quota(acc, mode)
    # Live quota used up: further generations run simulated (see auth.charge_with_fallback).
    q["fallback"] = mode == "live" and q["remaining"] == 0
    if q["fallback"]:
        q["mock"] = auth.quota(acc, "mock")
    return {"id": acc.id, "name": acc.name, "email": acc.email, "type": acc.type, "quota": q}


@app.post("/api/auth/register")
def register(body: RegisterBody, request: Request, response: Response,
             db: Session = Depends(get_db)):
    auth.rate_limit(f"register:{auth.client_ip(request)}", 5, 3600)
    email = body.email.lower()
    if db.scalar(select(Account).where(Account.email == email)):
        raise HTTPException(409, detail={"key": "errors.email_taken"})
    # The invite is consumed in the same transaction that creates the account.
    if get_settings().registration_requires_invite and not (
            body.invite_code and auth.consume_invite(db, body.invite_code)):
        db.rollback()
        raise HTTPException(403, detail={"key": "errors.invite_invalid"})
    acc = Account(name=body.name.strip(), email=email, type=body.type,
                  region_coarse=body.region_coarse, password_hash=auth.hash_password(body.password))
    db.add(acc)
    db.commit()
    auth.start_session(db, response, acc)
    return _me(acc)


@app.post("/api/auth/login")
def login(body: LoginBody, request: Request, response: Response, db: Session = Depends(get_db)):
    auth.rate_limit(f"login:{auth.client_ip(request)}", 10, 600)
    acc = db.scalar(select(Account).where(Account.email == body.email.lower()))
    if acc is None or not acc.is_active or not auth.verify_password(body.password, acc.password_hash):
        raise HTTPException(401, detail={"key": "errors.login_failed"})
    auth.start_session(db, response, acc)
    return _me(acc)


@app.post("/api/auth/jury")
def jury_login(request: Request, response: Response, db: Session = Depends(get_db)):
    """One-click access for the competition jury: a shared account with its own small
    generation limit (the global daily cap still applies)."""
    s = get_settings()
    if not s.jury_login_enabled:
        raise HTTPException(404, detail={"key": "errors.not_found"})
    auth.rate_limit(f"jury:{auth.client_ip(request)}", 20, 3600)
    acc = db.scalar(select(Account).where(Account.type == "jury"))
    if acc is None:
        acc = Account(name="Jury", type="jury", generation_limit=s.jury_generation_limit)
        db.add(acc)
        db.commit()
    auth.start_session(db, response, acc)
    return _me(acc)


@app.get("/api/locations")
def locations(db: Session = Depends(get_db), acc: Account | None = Depends(optional_account)):
    """Public positions of hanging tiles (rounded as the owner chose) for the map."""
    out = []
    for i in db.scalars(select(Instance).where(Instance.geo_lat.is_not(None))):
        if i.design.status != "published" and not (acc and acc.id == i.account_id):
            continue
        g = _geo(i, acc)
        if g:
            out.append({"id": i.id, "lat": g["lat"], "lon": g["lon"], "title": i.design.title, "title_en": i.design.title_en,
                        "place": i.location_coarse,
                        "preview_url": _file_url((i.design.files or {}).get("preview"),
                                                 _preview_version(i.design))})
    return out


@app.post("/api/auth/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    auth.end_session(db, request, response)
    return {"ok": True}


@app.get("/api/auth/me")
def me(acc: Account | None = Depends(optional_account)):
    return _me(acc) if acc else None


# -- helpers --------------------------------------------------------------------------
def _clean_image(data: bytes, content_type: str) -> tuple[bytes, int, int]:
    """Decode, apply EXIF orientation and re-encode WITHOUT metadata (no GPS in the data)."""
    try:
        im = Image.open(io.BytesIO(data))
        im.load()
    except (UnidentifiedImageError, OSError):
        raise HTTPException(422, detail={"key": "errors.image_unreadable"})
    im = ImageOps.exif_transpose(im)
    fmt = ALLOWED_IMAGE_TYPES[content_type]
    if fmt == "JPEG" and im.mode not in ("RGB", "L"):
        im = im.convert("RGB")
    buf = io.BytesIO()
    im.save(buf, format=fmt, **({"quality": 95} if fmt in ("JPEG", "WEBP") else {}))
    return buf.getvalue(), im.width, im.height


async def _read_image(file: UploadFile) -> tuple[bytes, str, int, int]:
    ct = (file.content_type or "").lower()
    if ct not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(415, detail={"key": "errors.image_type"})
    data = await file.read()
    if len(data) > get_settings().max_upload_mb * 1024 * 1024:
        raise HTTPException(413, detail={"key": "errors.image_too_large"})
    clean, w, h = _clean_image(data, ct)
    return clean, ct, w, h


def _design_or_404(db: Session, design_id: str) -> Design:
    d = db.get(Design, design_id)
    if d is None:
        d = db.scalar(select(Design).where(Design.code == design_id))
    if d is None:
        raise HTTPException(404, detail={"key": "errors.not_found"})
    return d


def _file_url(key: str | None, version: str | None = None) -> str | None:
    if not key:
        return None
    return f"/api/files/{key}" + (f"?v={version}" if version else "")


PREVIEW_STYLE = "m1"  # bump when the preview rendering changes


def _preview_version(d: Design) -> str | None:
    return f"{d.heightfield_sha256[:10]}{PREVIEW_STYLE}" if d.heightfield_sha256 else None


def serialize_design(d: Design, db: Session, full: bool = False,
                     viewer: Account | None = None) -> dict:
    n_inst = db.scalar(select(func.count()).select_from(Instance)
                       .where(Instance.design_id == d.id)) or 0
    out = {
        "id": d.id, "code": d.code, "title": d.title, "description": d.description,
        "source_type": d.source_type, "surface_type": d.surface_type,
        "status": d.status, "stage": d.stage, "parent_design_id": d.parent_design_id,
        "simulated": bool(d.simulated), "title_en": d.title_en, "description_en": d.description_en,
        "is_original": d.is_original, "license": d.license,
        # versioned by the height-field hash, so a re-export is never hidden by caches
        "preview_url": _file_url((d.files or {}).get("preview"), _preview_version(d)),
        "preview_3x3_url": _file_url((d.files or {}).get("preview_3x3"), _preview_version(d)),
        "tripo_render_url": _file_url((d.files or {}).get("tripo_render")),
        "instance_count": n_inst, "created_at": d.created_at.isoformat(),
        "pipeline_version": d.pipeline_version,
        "is_mine": viewer is not None and d.author_account_id == viewer.id,
        "shape": (d.pipeline_params or {}).get("shape", "square"),
    }
    if full:
        out.update({
            "params": d.pipeline_params, "metrics": d.metrics, "checks": d.checks,
            "model_seed": d.model_seed, "texture_seed": d.texture_seed,
            "raster_seed": d.raster_seed, "tripo_model_version": d.tripo_model_version,
            "tripo_texture_version": d.tripo_texture_version,
            "heightfield_sha256": d.heightfield_sha256,
            "has_package": bool((d.files or {}).get("package")),
            "interface_version": d.interface_version,
            "lineage": _lineage(db, d),
            "children": [{"id": c.id, "code": c.code, "title": c.title, "title_en": c.title_en} for c in
                         db.scalars(select(Design).where(Design.parent_design_id == d.id))],
        })
    return out


def _lineage(db: Session, d: Design) -> list[dict]:
    chain, cur, seen = [], d, set()
    while cur.parent_design_id and cur.parent_design_id not in seen:
        seen.add(cur.parent_design_id)
        cur = db.get(Design, cur.parent_design_id)
        if cur is None:
            break
        chain.append({"id": cur.id, "code": cur.code, "title": cur.title, "title_en": cur.title_en})
    return chain


# -- meta -----------------------------------------------------------------------------
@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/config")
def config():
    s = get_settings()
    return {
        "tripo_mode": s.tripo_mode, "tripo_key_configured": bool(s.tripo_api_key.get_secret_value()),
        "invite_required": s.registration_requires_invite,
        "jury_login": s.jury_login_enabled,
        "pipeline_version": C.PIPELINE_VERSION, "interface_version": C.INTERFACE_VERSION,
        "printers": C.PRINTER_PROFILES, "materials": C.MATERIALS, "processes": C.PROCESSES,
        "tool_materials": C.TOOL_MATERIALS, "tile_sizes_mm": C.TILE_SIZES_MM, "tile_shapes": C.TILE_SHAPES,
        "limits": {
            "macro_depth_max_mm": C.MACRO_DEPTH_MAX_MM, "meso_depth_max_mm": C.MESO_DEPTH_MAX_MM,
            "channel_depth_mm": C.BOOSTER_CHANNEL_DEPTH_RANGE_MM,
            "channel_width_mm": C.BOOSTER_CHANNEL_WIDTH_RANGE_MM,
            "clay_shrink_pct": C.CLAY_SHRINK_RANGE_PCT,
            "max_upload_mb": s.max_upload_mb,
        },
    }


@app.get("/api/library")
def library():
    return list(svc.load_library().values())


# -- uploads & designs ----------------------------------------------------------------
@app.post("/api/uploads")
async def upload(file: UploadFile = File(...), db: Session = Depends(get_db),
                 acc: Account = Depends(current_account)):
    auth.rate_limit(f"upload:{acc.id}", 30, 3600)
    data, ct, w, h = await _read_image(file)
    sha = hashlib.sha256(data).hexdigest()
    ext = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}[ct]
    key = f"uploads/{sha[:2]}/{sha}.{ext}"
    get_storage().put(key, data, ct)
    up = Upload(key=key, filename=re.sub(r"[^\w.\-]", "_", file.filename or f"photo.{ext}"),
                content_type=ct, size=len(data), sha256=sha, width=w, height=h)
    db.add(up)
    db.commit()
    warnings = ["upload.warn_small"] if min(w, h) < 256 else []
    return {"upload_id": up.id, "width": w, "height": h, "warnings": warnings}


class DesignCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    source_type: str = Field(pattern="^(photo|procedural)$")  # text/hybrid: v1
    upload_id: str | None = None
    surface_type: str | None = None
    enable_image_autofix: bool = False


@app.post("/api/designs")
def create_design(body: DesignCreate, db: Session = Depends(get_db),
                  acc: Account = Depends(current_account)):
    lib = svc.load_library()
    if body.source_type == "photo" and not body.upload_id:
        raise HTTPException(422, detail={"key": "errors.upload_required"})
    if body.source_type == "procedural" and body.surface_type not in lib:
        raise HTTPException(422, detail={"key": "errors.unknown_surface"})
    if body.upload_id and db.get(Upload, body.upload_id) is None:
        raise HTTPException(404, detail={"key": "errors.not_found"})
    up = db.get(Upload, body.upload_id) if body.upload_id else None
    d = Design(title=body.title, description=body.description, source_type=body.source_type,
               surface_type=body.surface_type, source_upload_id=body.upload_id,
               source_photo_key=up.key if up else None,
               enable_image_autofix=body.enable_image_autofix,
               author_account_id=acc.id, is_original=True)
    db.add(d)
    db.commit()
    return serialize_design(d, db, full=True)


@app.get("/api/designs")
def list_designs(status: str | None = "published", source_type: str | None = None,
                 surface_type: str | None = None, db: Session = Depends(get_db),
                 acc: Account | None = Depends(optional_account)):
    q = select(Design).order_by(Design.created_at.desc())
    # Drafts are private: "all" = published + the caller's own drafts.
    mine = Design.author_account_id == acc.id if acc else None
    if status == "all":
        q = q.where((Design.status == "published") | mine) if acc is not None else \
            q.where(Design.status == "published")
    elif status == "mine":
        if acc is None:
            return []
        q = q.where(mine)
    else:
        q = q.where(Design.status == (status or "published"))
    if source_type:
        q = q.where(Design.source_type == source_type)
    if surface_type:
        q = q.where(Design.surface_type == surface_type)
    return [serialize_design(d, db, viewer=acc) for d in db.scalars(q.limit(200))]


@app.get("/api/designs/{design_id}")
def get_design(design_id: str, db: Session = Depends(get_db),
               acc: Account | None = Depends(optional_account)):
    d = _design_or_404(db, design_id)
    if not _visible(d, acc):
        raise HTTPException(404, detail={"key": "errors.not_found"})
    return serialize_design(d, db, full=True, viewer=acc)


def _start_job(db: Session, design: Design, kind: str, acc: Account | None = None) -> dict:
    running = db.scalar(select(Job).where(Job.design_id == design.id, Job.kind == kind,
                                          Job.status.in_(("queued", "running"))))
    if running:
        return {"job_id": running.id}
    job = Job(design_id=design.id, kind=kind, account_id=acc.id if acc else None)
    # Every generation that calls Tripo is charged to the account (reference tiles are free).
    if kind == "generate" and acc is not None and design.surface_type not in svc.PROCEDURAL:
        mode = auth.charge_with_fallback(db, acc, get_settings().tripo_mode)
        job.tripo_mode, job.counted = mode, True
    db.add(job)
    db.commit()
    enqueue(kind, job.id)
    return {"job_id": job.id}


@app.post("/api/designs/{design_id}/generate")
def generate(design_id: str, db: Session = Depends(get_db),
             acc: Account = Depends(current_account)):
    d = _design_or_404(db, design_id)
    _require_owner(d, acc)
    if d.status == "published":
        raise HTTPException(409, detail={"key": "errors.published_locked"})
    return _start_job(db, d, "generate", acc)


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str, db: Session = Depends(get_db)):
    j = db.get(Job, job_id)
    if j is None:
        raise HTTPException(404, detail={"key": "errors.not_found"})
    return {"id": j.id, "design_id": j.design_id, "kind": j.kind, "status": j.status,
            "progress": j.progress, "step": j.step, "error": j.error, "error_key": j.error_key,
            "simulated": j.kind == "generate" and j.tripo_mode == "mock" and get_settings().tripo_mode == "live"}


@app.get("/api/designs/{design_id}/job")
def latest_job(design_id: str, kind: str = "generate", db: Session = Depends(get_db),
               acc: Account | None = Depends(optional_account)):
    d = _design_or_404(db, design_id)
    if not _visible(d, acc):
        raise HTTPException(404, detail={"key": "errors.not_found"})
    j = db.scalar(select(Job).where(Job.design_id == d.id, Job.kind == kind)
                  .order_by(Job.created_at.desc()))
    if j is None:
        raise HTTPException(404, detail={"key": "errors.not_found"})
    return get_job(j.id, db)


@app.patch("/api/designs/{design_id}/params")
def patch_params(design_id: str, updates: dict, db: Session = Depends(get_db),
                 acc: Account = Depends(current_account)):
    d = _design_or_404(db, design_id)
    _require_owner(d, acc)
    if d.status == "published":
        raise HTTPException(409, detail={"key": "errors.published_locked"})
    if d.stage in ("new", "generating", "failed"):
        raise HTTPException(409, detail={"key": "errors.not_generated"})
    updates.pop("resolution_px", None)
    try:
        p = svc.params_of(d).with_updates(updates)
        errs = p.validate()
        if errs:
            raise ValueError("; ".join(errs))
        result = svc.compute_tile(d, p.with_updates(
            {"resolution_px": get_settings().pipeline_preview_px}))
    except (TypeError, ValueError) as e:
        raise HTTPException(422, detail={"key": "errors.invalid_params", "message": str(e)})
    d.pipeline_params = p.to_dict()
    svc._sync_columns(d, p)
    if d.stage == "exported":
        d.stage = "ready"  # package no longer matches the parameters
    db.commit()
    return svc.preview_payload(d, result)


_preview_cache: dict = {}


@app.get("/api/designs/{design_id}/preview")
def preview(design_id: str, n: int = 192, db: Session = Depends(get_db),
            acc: Account | None = Depends(optional_account)):
    d = _design_or_404(db, design_id)
    if not _visible(d, acc):
        raise HTTPException(404, detail={"key": "errors.not_found"})
    if d.stage in ("new", "generating", "failed"):
        raise HTTPException(409, detail={"key": "errors.not_generated"})
    p = svc.params_of(d, get_settings().pipeline_preview_px)
    n = max(48, min(int(n), 192))
    key = (d.id, d.code, json.dumps(d.pipeline_params, sort_keys=True), n)
    cached = _preview_cache.get(key)
    if cached is None:
        cached = svc.preview_payload(d, svc.compute_tile(d, p), n=n)
        if len(_preview_cache) > 64:
            _preview_cache.clear()
        _preview_cache[key] = cached
    return cached


@app.post("/api/designs/{design_id}/export")
def export(design_id: str, db: Session = Depends(get_db),
           acc: Account = Depends(current_account)):
    d = _design_or_404(db, design_id)
    _require_owner(d, acc)
    if d.stage not in ("ready", "exported"):
        raise HTTPException(409, detail={"key": "errors.not_generated"})
    auth.rate_limit(f"export:{acc.id}", 20, 3600)
    return _start_job(db, d, "export", acc)


@app.get("/api/designs/{design_id}/package")
def package(design_id: str, db: Session = Depends(get_db),
            acc: Account | None = Depends(optional_account)):
    d = _design_or_404(db, design_id)
    if not _visible(d, acc):
        raise HTTPException(404, detail={"key": "errors.not_found"})
    key = (d.files or {}).get("package")
    if not key or d.stage != "exported":
        raise HTTPException(404, detail={"key": "errors.no_package"})
    return Response(get_storage().get(key), media_type="application/zip", headers={
        "Content-Disposition": f'attachment; filename="{d.code or d.id}.zip"'})


class PublishBody(BaseModel):
    license_confirmed: bool


@app.post("/api/designs/{design_id}/publish")
def publish(design_id: str, body: PublishBody, db: Session = Depends(get_db),
            acc: Account = Depends(current_account)):
    d = _design_or_404(db, design_id)
    _require_owner(d, acc)
    if not body.license_confirmed:
        raise HTTPException(422, detail={"key": "errors.license_required"})
    if d.stage != "exported":
        raise HTTPException(409, detail={"key": "errors.export_first"})
    if any(c.get("status") == "fail" for c in d.checks or []):
        raise HTTPException(409, detail={"key": "errors.checks_failed"})
    d.status = "published"
    db.commit()
    return serialize_design(d, db, full=True)


@app.post("/api/designs/{design_id}/remix")
def remix(design_id: str, db: Session = Depends(get_db),
          acc: Account = Depends(current_account)):
    src = _design_or_404(db, design_id)
    if not _visible(src, acc):
        raise HTTPException(404, detail={"key": "errors.not_found"})
    if src.stage in ("new", "generating", "failed"):
        raise HTTPException(409, detail={"key": "errors.not_generated"})
    child = Design(title=f"{src.title} (remix)", description=src.description,
                   source_type=src.source_type, surface_type=src.surface_type,
                   source_upload_id=src.source_upload_id, source_photo_key=src.source_photo_key,
                   parent_design_id=src.id, is_original=False,
                   author_account_id=acc.id, model_seed=src.model_seed,
                   texture_seed=src.texture_seed, raster_seed=src.raster_seed,
                   tripo_model_version=src.tripo_model_version,
                   tripo_texture_version=src.tripo_texture_version,
                   raw_raster_key=src.raw_raster_key, pipeline_params=dict(src.pipeline_params),
                   pipeline_version=src.pipeline_version, stage="ready",
                   files={k: v for k, v in (src.files or {}).items()
                          if k in ("tripo_glb", "tripo_render")})
    db.add(child)
    db.commit()
    return serialize_design(child, db, full=True)


# -- files ----------------------------------------------------------------------------
PUBLIC_FILE = re.compile(r"^(designs/[0-9a-f]{32}/(preview|preview_3x3|tripo_render)\.png|"
                         r"observations/[0-9a-f]{2}/[0-9a-f]{64}\.(jpg|png|webp))$")


@app.get("/api/files/{key:path}")
def files(key: str):
    # Source photos are never served publicly (people / locations, brief 12.3).
    if not PUBLIC_FILE.match(key):
        raise HTTPException(404, detail={"key": "errors.not_found"})
    st = get_storage()
    if not st.exists(key):
        raise HTTPException(404, detail={"key": "errors.not_found"})
    ext = key.rsplit(".", 1)[-1]
    mt = {"png": "image/png", "jpg": "image/jpeg", "webp": "image/webp"}[ext]
    return Response(st.get(key), media_type=mt, headers={"Cache-Control": "max-age=300"})


# -- instances & observations ---------------------------------------------------------
class InstanceCreate(BaseModel):
    design_id: str
    material: str = Field(pattern="^(clay|concrete|lime|loam)$")
    process: str = Field(pattern="^(press_mould|matrix_down|stamp_down)$")
    orientation_deg: float = Field(ge=0, lt=360)  # mandatory (brief 9.4)
    format: str = Field("1x1", pattern="^(1x1|2x1|2x2)$")
    stage: int = Field(1, ge=1, le=3)
    tool_material: str | None = None
    release_agent: str | None = None
    retarder_washed: bool = False
    back_type: str | None = Field(None, pattern="^(shell|solid|waffle)$")
    channels: str = Field("none", pattern="^(none|edge_half|through)$")
    booster: bool = False
    booster_recipe: str | None = Field(None, max_length=1000)  # how the moss starter was made
    booster_date: date | None = None
    mounting_adapter: str | None = Field(None, pattern="^(wall|fence|facade|post|tree|other)$")
    mounting_detail: str | None = Field(None, max_length=200)
    geo_lat: float | None = Field(None, ge=-90, le=90)
    geo_lon: float | None = Field(None, ge=-180, le=180)
    geo_visibility: str = Field("approx", pattern="^(hidden|approx|exact)$")
    cast_date: date | None = None
    installed_date: date | None = None
    inclination_deg: float | None = Field(None, ge=0, le=180)
    height_above_ground_m: float | None = Field(None, ge=0, le=100)
    shading: str | None = Field(None, pattern="^(full_sun|partial|shade|deep_shade)$")
    substrate: str | None = None
    location_coarse: str | None = Field(None, max_length=200)
    material_details: dict = Field(default_factory=dict)
    notes: str | None = None


def _geo(i: Instance, viewer: Account | None) -> dict | None:
    """Exact for the owner; otherwise rounded (~100 m) or hidden as the owner chose."""
    if i.geo_lat is None or i.geo_lon is None:
        return None
    if viewer is not None and viewer.id == i.account_id:
        return {"lat": i.geo_lat, "lon": i.geo_lon, "precision": "exact", "visibility": i.geo_visibility}
    if i.geo_visibility == "hidden":
        return None
    if i.geo_visibility == "exact":
        return {"lat": round(i.geo_lat, 6), "lon": round(i.geo_lon, 6), "precision": "exact"}
    return {"lat": round(i.geo_lat, 3), "lon": round(i.geo_lon, 3), "precision": "approx"}


def serialize_instance(i: Instance, viewer: Account | None = None) -> dict:
    return {
        "is_mine": viewer is not None and viewer.id == i.account_id,
        "geo": _geo(i, viewer), "mounting_detail": i.mounting_detail,
        "design_shape": (i.design.pipeline_params or {}).get("shape", "square"),
        "design_preview_url": _file_url((i.design.files or {}).get("preview"), _preview_version(i.design)),
        "id": i.id, "design_id": i.design_id, "design_code": i.design.code,
        "design_title": i.design.title, "design_title_en": i.design.title_en, "material": i.material, "process": i.process,
        "format": i.format, "stage": i.stage, "orientation_deg": i.orientation_deg,
        "inclination_deg": i.inclination_deg, "booster": i.booster,
        "booster_recipe": i.booster_recipe, "mounting_adapter": i.mounting_adapter,
        "installed_date": i.installed_date, "cast_date": i.cast_date, "shading": i.shading,
        "location_coarse": i.location_coarse, "status": i.status, "channels": i.channels,
        "height_above_ground_m": i.height_above_ground_m, "notes": i.notes,
        "observations": [{
            "id": o.id, "observed_at": o.observed_at, "photo_url": _file_url(o.photo_key),
            "species": o.species, "notes": o.notes, "weight_g": o.weight_g,
            "observer_role": o.observer_role, "green_fraction": o.green_fraction,
        } for o in i.observations if o.moderation_status == "approved"],
    }


@app.post("/api/instances")
def create_instance(body: InstanceCreate, db: Session = Depends(get_db),
                    acc: Account = Depends(current_account)):
    d = _design_or_404(db, body.design_id)
    if not _visible(d, acc):
        raise HTTPException(404, detail={"key": "errors.not_found"})
    if not d.code:
        raise HTTPException(409, detail={"key": "errors.not_generated"})
    base = "BT-" + d.code.removeprefix("BT-D-").removeprefix("BT-")
    n = (db.scalar(select(func.count()).select_from(Instance)
                   .where(Instance.design_id == d.id)) or 0) + 1
    data = body.model_dump(exclude={"design_id"})
    for k in ("booster_date", "cast_date", "installed_date"):
        data[k] = data[k].isoformat() if data[k] else None
    if acc.type == "school" and data["geo_visibility"] == "exact":
        data["geo_visibility"] = "approx"  # privacy: never exact positions for schools
    inst = Instance(id=f"{base}-{n:03d}", design_id=d.id, account_id=acc.id, **data)
    db.add(inst)
    db.commit()
    db.refresh(inst)
    return serialize_instance(inst, acc)


@app.get("/api/instances/{instance_id}")
def get_instance(instance_id: str, db: Session = Depends(get_db),
                 acc: Account | None = Depends(optional_account)):
    i = db.get(Instance, instance_id.upper())
    if i is None:
        raise HTTPException(404, detail={"key": "errors.not_found"})
    return serialize_instance(i, acc)


@app.get("/api/lookup/{code}")
def lookup(code: str, db: Session = Depends(get_db),
           acc: Account | None = Depends(optional_account)):
    """A tile code: either one hanging tile (BT-XXXXXX-NNN) or a pattern (BT-XXXXXX) with all
    its hanging tiles, numbered in order."""
    c = code.strip().upper()
    inst = db.get(Instance, c)
    if inst is not None:
        return {"kind": "instance", "instance": serialize_instance(inst, acc)}
    d = db.scalar(select(Design).where(Design.code.in_((c, c.replace("BT-", "BT-D-", 1)))))
    if d is None or not _visible(d, acc):
        raise HTTPException(404, detail={"key": "errors.not_found"})
    tiles = sorted(d.instances, key=lambda i: i.id)
    return {"kind": "design", "design": serialize_design(d, db, viewer=acc),
            "instances": [serialize_instance(i, acc) for i in tiles]}


@app.get("/api/designs/{design_id}/instances")
def design_instances(design_id: str, db: Session = Depends(get_db),
                     acc: Account | None = Depends(optional_account)):
    d = _design_or_404(db, design_id)
    if not _visible(d, acc):
        raise HTTPException(404, detail={"key": "errors.not_found"})
    return [serialize_instance(i, acc) for i in sorted(d.instances, key=lambda i: i.id)]


@app.get("/api/instances/{instance_id}/reference-card.pdf")
def reference_card(instance_id: str, db: Session = Depends(get_db)):
    from biotile_geometry.pdfs import reference_card as card

    i = db.get(Instance, instance_id.upper())
    if i is None:
        raise HTTPException(404, detail={"key": "errors.not_found"})
    url = f"{get_settings().public_base_url.rstrip('/')}/observe/{i.id}"
    return Response(card(i.id, url), media_type="application/pdf", headers={
        "Content-Disposition": f'inline; filename="{i.id}-reference-card.pdf"'})


@app.get("/api/reference-card.pdf")
def blank_reference_card():
    from biotile_geometry.pdfs import reference_card as card

    return Response(card(), media_type="application/pdf")


@app.post("/api/instances/{instance_id}/observations")
async def add_observation(instance_id: str, observed_at: date = Form(...),
                          observer_role: str = Form("teacher"), notes: str | None = Form(None),
                          weight_g: float | None = Form(None), species: str = Form("[]"),
                          photo: UploadFile | None = File(None), db: Session = Depends(get_db),
                          acc: Account = Depends(current_account)):
    auth.rate_limit(f"observe:{acc.id}", 60, 3600)
    import json

    i = db.get(Instance, instance_id.upper())
    if i is None:
        raise HTTPException(404, detail={"key": "errors.not_found"})
    if observer_role not in ("teacher", "student_group", "citizen", "researcher"):
        raise HTTPException(422, detail={"key": "errors.invalid_role"})
    try:
        sp = json.loads(species)
        assert isinstance(sp, list)
        sp = [{"name": str(s.get("name", ""))[:200], "taxon_ref": s.get("taxon_ref"),
               "group": s.get("group") if s.get("group") in
               ("moss", "lichen", "algae", "fungus", "invertebrate", "plant") else None,
               "certainty": s.get("certainty") if s.get("certainty") in
               ("certain", "likely", "unsure") else "unsure"} for s in sp if s.get("name")]
    except (ValueError, AssertionError, AttributeError):
        raise HTTPException(422, detail={"key": "errors.invalid_species"})
    key = None
    if photo is not None and photo.filename:
        data, ct, _, _ = await _read_image(photo)
        sha = hashlib.sha256(data).hexdigest()
        ext = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}[ct]
        key = get_storage().put(f"observations/{sha[:2]}/{sha}.{ext}", data, ct)
    o = Observation(instance_id=i.id, observed_at=observed_at.isoformat(), photo_key=key,
                    observer_role=observer_role, notes=notes, weight_g=weight_g, species=sp)
    db.add(o)
    db.commit()
    db.refresh(i)
    return serialize_instance(i, acc)
