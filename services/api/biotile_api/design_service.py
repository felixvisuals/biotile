"""Glue between DB, storage, Tripo and the geometry package (used by API and worker)."""

from __future__ import annotations

import base64
import hashlib
import io
import json
import logging
import random
from datetime import UTC, datetime

import numpy as np
from biotile_geometry import constants as C
from biotile_geometry.metrics import compute_metrics
from biotile_geometry.package import build_package, png_bytes
from biotile_geometry.pdfs import preview_image
from biotile_geometry.pipeline import (
    TileParams,
    TileResult,
    joint_lines,
    run_procedural,
    run_stage_b,
    stamp_front_code,
    wall_field,
)
from biotile_geometry.rasterize import RawRaster, load_mesh, rasterize_mesh
from biotile_geometry.tools import ToolFrame, bed_check, bed_fit_estimate, build_toolset
from scipy import ndimage
from sqlalchemy import select

from .models import Design, Job, SessionLocal, TripoJob, Upload
from .settings import get_settings
from .storage import get_storage
from .tripo import TripoError, image_to_model_request, make_client, poll_until_done
from .tripo.client import MODEL_VERSION, TEXTURE_VERSION, redact

log = logging.getLogger("biotile.pipeline")

PROCEDURAL = {"REF-FLAT": "ref_flat", "REF-GEO": "ref_geo"}


def load_library() -> dict:
    s = get_settings()
    doc = json.loads((s.library_dir / "library.json").read_text())
    return {e["id"]: e for e in doc["surfaces"]}


def tripo_client(mode: str | None = None):
    s = get_settings()
    return make_client(mode or s.tripo_mode, s.tripo_api_key.get_secret_value(), s.tripo_fixtures_dir,
                       record=s.tripo_record, base_url=s.tripo_base_url,
                       mock_task_seconds=s.mock_task_seconds)


def default_params(surface_type: str | None) -> TileParams:
    p = TileParams(resolution_px=get_settings().pipeline_internal_px)
    entry = load_library().get(surface_type or "")
    if entry:
        updates = dict(entry.get("recommended_bands") or {})
        updates["functional"] = {"template": entry.get("recommended_functional_template",
                                                       "diagonal_cascade")}
        p = p.with_updates(updates)
    return p


def params_of(design: Design, resolution: int | None = None) -> TileParams:
    p = TileParams.from_dict(design.pipeline_params) if design.pipeline_params else \
        default_params(design.surface_type)
    if resolution:
        p = p.with_updates({"resolution_px": resolution})
    return p


# -- raw raster storage ---------------------------------------------------------------
def save_raw(design: Design, raw: RawRaster) -> str:
    buf = io.BytesIO()
    np.savez_compressed(buf, z=raw.z.astype(np.float32), extent=raw.extent, flipped=raw.flipped,
                        n_faces=raw.n_faces)
    key = f"designs/{design.id}/raw_raster.npz"
    get_storage().put(key, buf.getvalue(), "application/octet-stream")
    return key


def load_raw(key: str) -> RawRaster:
    d = np.load(io.BytesIO(get_storage().get(key)))
    return RawRaster(z=d["z"].astype(np.float64), extent=float(d["extent"]),
                     flipped=bool(d["flipped"]), n_faces=int(d["n_faces"]))


_raw_cache: dict[str, RawRaster] = {}


def compute_tile(design: Design, p: TileParams) -> TileResult:
    kind = PROCEDURAL.get(design.surface_type or "")
    if kind:
        result = run_procedural(kind, p)
    else:
        if not design.raw_raster_key:
            raise ValueError("design has no generated sample yet")
        raw = _raw_cache.get(design.raw_raster_key)
        if raw is None:
            raw = load_raw(design.raw_raster_key)
            _raw_cache.clear()  # keep memory bounded: one design at a time
            _raw_cache[design.raw_raster_key] = raw
        result = run_stage_b(raw, p)
    return stamp_front_code(result, design.code) if design.code else result


def _b64(a: np.ndarray) -> str:
    return base64.b64encode(np.ascontiguousarray(a, dtype=np.float32).tobytes()).decode()


def preview_payload(design: Design, result: TileResult, n: int = 192) -> dict:
    """Everything the 3D editor needs: the tile front (NaN outside the outline), a seamless
    wall window of 3 x 3 tile sizes with the joint lines, sizes and checks."""
    p = result.params
    lat = result.lattice
    ny, nx = result.front.shape
    k = n / ny
    front = ndimage.zoom(result.front, k, order=1)
    inside = ndimage.zoom(result.mask.astype(np.float32), k, order=1) > 0.5
    front = np.where(inside, front, np.nan)
    wall, _ = wall_field(result, int(n * 1.6))
    w, h = lat.bbox
    fr = ToolFrame.from_params(p)
    bed = bed_fit_estimate(p)
    return {
        "design_id": design.id,
        "code": design.code,
        "shape": p.shape,
        "size_mm": p.tile_size_mm,
        "bbox_mm": [w, h],
        "thickness_mm": C.TILE_THICKNESS_MM,
        "front": {"nx": int(front.shape[1]), "ny": int(front.shape[0]), "b64": _b64(front)},
        "wall": {"n": int(wall.shape[0]), "extent_mm": lat.size * 3, "b64": _b64(wall)},
        "joints": joint_lines(lat, 3),
        "mould_mm": [round(max(w, h) * fr.s + 2 * fr.F, 1),
                     round(C.MATRIX_BASE_MM + C.MATRIX_PLINTH_MM + C.TOTAL_RELIEF_MAX_MM * fr.s, 1)],
        "checks": [c.to_dict() for c in result.checks] + [bed_check(bed).to_dict()],
        "bed": bed,
        "structure_angle_deg": result.structure_angle_deg,
        "anisotropy": result.anisotropy,
        "rotation_deg": result.rotation_deg,
        "params": result.params.to_dict(),
        "tool_scale": result.params.tool_scale,
    }


# -- jobs -----------------------------------------------------------------------------
def _job_update(job_id: str, **kw) -> None:
    with SessionLocal() as db:
        job = db.get(Job, job_id)
        for k, v in kw.items():
            setattr(job, k, v)
        db.commit()


def assign_code(db, design: Design) -> str:
    """Tile code of the pattern, created at the first generation: BT- + 6 characters.
    Hanging tiles get -001, -002, ... appended (see /api/instances)."""
    if design.code:
        return design.code
    alphabet = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
    seed = f"{design.source_upload_id or design.surface_type}:{design.id}"
    for attempt in range(50):
        h = int(hashlib.sha256(f"{seed}:{attempt}".encode()).hexdigest(), 16)
        code = "BT-" + "".join(alphabet[(h >> (5 * i)) % len(alphabet)] for i in range(6))
        if db.scalar(select(Design).where(Design.code == code)) is None:
            design.code = code
            return code
    raise RuntimeError("could not allocate a unique tile code")


def _ensure_seeds(design: Design) -> None:
    if design.model_seed is None:
        # Seeds are stored with the design -> reproducible (brief 7.3).
        rnd = random.Random(design.id)
        design.model_seed = rnd.randrange(1, 2**31 - 1)
        design.texture_seed = design.model_seed
        design.raster_seed = rnd.randrange(1, 2**31 - 1)


def run_generate(job_id: str) -> None:
    """Upload -> Tripo image-to-model -> GLB -> raw raster -> first preview."""
    with SessionLocal() as db:
        job = db.get(Job, job_id)
        design = db.get(Design, job.design_id)
        job.status, job.step, job.progress = "running", "prepare", 2
        design.stage = "generating"
        _ensure_seeds(design)
        assign_code(db, design)
        db.commit()
        try:
            if design.surface_type in PROCEDURAL:
                design.pipeline_version = C.PIPELINE_VERSION
                design.capture_method = None
            else:
                _generate_sample(db, job, design)
            p = params_of(design)
            design.pipeline_params = p.to_dict()
            _sync_columns(design, p)
            design.stage = "ready"
            job.status, job.step, job.progress = "success", "done", 100
            db.commit()
        except TripoError as e:
            db.rollback()
            _fail(job_id, design.id, str(e), e.user_message_key)
        except Exception as e:  # noqa: BLE001 - surface every failure to the UI
            log.exception("generate failed")
            db.rollback()
            _fail(job_id, design.id, f"{type(e).__name__}: {e}", "errors.pipeline")


def _fail(job_id: str, design_id: str, msg: str, key: str) -> None:
    with SessionLocal() as db:
        job = db.get(Job, job_id)
        job.status, job.error, job.error_key = "failed", msg[:2000], key
        d = db.get(Design, design_id)
        d.stage = "failed"
        db.commit()
        # Give the generation back if Tripo never accepted a task (no credits were spent).
        if job.counted and job.account_id:
            accepted = db.scalar(select(TripoJob).where(
                TripoJob.design_id == design_id, TripoJob.kind == "image_to_model",
                TripoJob.task_id.is_not(None), TripoJob.created_at >= job.created_at))
            if accepted is None:
                from .auth import refund_generation

                refund_generation(db, job.account_id, job.tripo_mode or "mock")
                job.counted = False
                db.commit()


def _generate_sample(db, job: Job, design: Design) -> None:
    # The job's mode wins: a live account past its quota is charged (and run) as mock.
    client = tripo_client(job.tripo_mode)
    design.simulated = (job.tripo_mode or get_settings().tripo_mode) == "mock"
    storage = get_storage()
    if design.source_type == "photo":
        upload = db.get(Upload, design.source_upload_id)
        image = storage.get(upload.key)
        content_type = upload.content_type
        filename = upload.filename
        if content_type == "image/webp":  # convert: WebP support of /v3/files unconfirmed
            from PIL import Image

            buf = io.BytesIO()
            Image.open(io.BytesIO(image)).convert("RGB").save(buf, format="PNG")
            image, content_type, filename = buf.getvalue(), "image/png", filename + ".png"
        hint = None
    else:  # library sample: synthetic stand-in in mock mode
        entry = load_library()[design.surface_type]
        image = f"library:{design.surface_type}".encode()
        content_type, filename = "image/png", f"{design.surface_type}.png"
        hint = entry.get("mock_fixture")
        if client.mode != "mock":
            raise ValueError("library samples without a photo need TRIPO_MODE=mock or the text "
                             "mode (v1)")

    tj = TripoJob(design_id=design.id, kind="upload", status="running")
    db.add(tj)
    job.step, job.progress = "tripo_upload", 5
    db.commit()
    token = client.upload_file(image, filename, content_type)
    tj.status, tj.completed_at = "success", datetime.now(UTC)

    req = image_to_model_request(token, design.model_seed, design.texture_seed,
                                 enable_image_autofix=design.enable_image_autofix)
    tj2 = TripoJob(design_id=design.id, kind="image_to_model", request=redact(req),
                   status="queued")
    db.add(tj2)
    design.tripo_model_version, design.tripo_texture_version = MODEL_VERSION, TEXTURE_VERSION
    job.step, job.progress = "tripo_generate", 10
    db.commit()
    task_id = (client.image_to_model(req, hint=hint) if client.mode == "mock"
               else client.image_to_model(req))
    tj2.task_id = task_id
    db.commit()

    def progress(info) -> None:
        tj2.status, tj2.progress = info.status, info.progress
        job.progress = 10 + int(info.progress * 0.6)
        db.commit()

    info = poll_until_done(client, task_id, on_progress=progress)
    tj2.raw_response = redact(info.raw)
    tj2.credits_consumed = info.credits_consumed
    tj2.completed_at = datetime.now(UTC)
    if info.status != "success":
        tj2.error_code = info.error_code
        tj2.status = info.status
        db.commit()
        raise TripoError(info.error_code or -1, info.error_message or f"task {info.status}")
    tj2.status = "success"
    if info.credits_consumed:
        from .models import Account

        acc = db.get(Account, design.author_account_id) if design.author_account_id else None
        if acc:
            acc.credits_used += float(info.credits_consumed)
    job.step, job.progress = "download", 72
    db.commit()

    glb = client.download(info.model_url)
    storage.put(f"designs/{design.id}/tripo_model.glb", glb, "model/gltf-binary")
    files = dict(design.files or {})
    files["tripo_glb"] = f"designs/{design.id}/tripo_model.glb"
    if info.rendered_image_url:
        try:
            storage.put(f"designs/{design.id}/tripo_render.png",
                        client.download(info.rendered_image_url), "image/png")
            files["tripo_render"] = f"designs/{design.id}/tripo_render.png"
        except Exception:  # noqa: BLE001 - render is optional
            log.warning("could not download rendered image")
    design.files = files

    job.step, job.progress = "rasterize", 80
    db.commit()
    mesh = load_mesh(io.BytesIO(glb), file_type="glb")
    raw = rasterize_mesh(mesh, get_settings().pipeline_internal_px, seed=design.raster_seed,
                         crop_fraction=C.RASTER_CROP_FRACTION)
    design.raw_raster_key = save_raw(design, raw)
    design.pipeline_version = C.PIPELINE_VERSION
    design.capture_method = "single_photo" if design.source_type == "photo" else None


def _sync_columns(design: Design, p: TileParams) -> None:
    design.functional_template = p.functional.template
    design.edge_mode = p.edge_mode
    design.texture_period_mm = p.texture_period_mm
    design.orientation_mode = p.orientation_mode
    design.interface_version = C.INTERFACE_VERSION


def run_export(job_id: str) -> None:
    with SessionLocal() as db:
        job = db.get(Job, job_id)
        design = db.get(Design, job.design_id)
        job.status, job.step, job.progress = "running", "relief", 5
        db.commit()
        try:
            p = params_of(design, get_settings().pipeline_internal_px)
            result = compute_tile(design, p)
            job.step, job.progress = "tools", 35
            db.commit()
            tools = build_toolset(result)
            job.step, job.progress = "metrics", 60
            db.commit()
            metrics = compute_metrics(result)
            sha = result.heightfield_hash()
            if not design.code:  # designs from before 0.3 get their code now
                assign_code(db, design)
                result = stamp_front_code(result, design.code)
                sha = result.heightfield_hash()
            job.step, job.progress = "package", 75
            db.commit()
            extra = {"title": design.title, "source_type": design.source_type,
                     "surface_type": design.surface_type, "model_seed": design.model_seed,
                     "texture_seed": design.texture_seed, "raster_seed": design.raster_seed,
                     "tripo_model_version": design.tripo_model_version,
                     "tripo_texture_version": design.tripo_texture_version,
                     "parent_design_id": design.parent_design_id}
            pkg = build_package(design.code, result, tools, metrics, extra)
            storage = get_storage()
            base = f"designs/{design.id}"
            storage.put(f"{base}/package.zip", pkg, "application/zip")
            storage.put(f"{base}/preview.png", png_bytes(preview_image(
                result.front, result.px_mm, size=640, mask=result.mask)), "image/png")
            wall, wall_px = wall_field(result, 1100)
            storage.put(f"{base}/preview_3x3.png",
                        png_bytes(preview_image(wall, wall_px, size=768)), "image/png")
            files = dict(design.files or {})
            files.update({"package": f"{base}/package.zip", "preview": f"{base}/preview.png",
                          "preview_3x3": f"{base}/preview_3x3.png"})
            design.files = files
            design.checks = [c.to_dict() for c in result.checks] + [
                bed_check(tools.bed_checks).to_dict()]
            design.metrics = {**metrics, "bed_checks": tools.bed_checks}
            design.heightfield_sha256 = sha
            design.pipeline_version = C.PIPELINE_VERSION
            design.stage = "exported"
            job.status, job.step, job.progress = "success", "done", 100
            db.commit()
        except Exception as e:  # noqa: BLE001
            log.exception("export failed")
            db.rollback()
            with SessionLocal() as db2:
                j = db2.get(Job, job_id)
                j.status, j.error, j.error_key = "failed", f"{type(e).__name__}: {e}"[:2000], \
                    "errors.pipeline"
                db2.commit()
