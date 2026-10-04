"""Relief pipeline: raw raster of a generated sample -> seamless tile front height field.

Stage A (slow, cached): mesh -> RawRaster (rasterize.py).
Stage B (fast, re-run on every editor change): RawRaster + TileParams -> TileResult.

The design ("pattern") lives on the index grid of a tiling lattice (lattice.py): square tiles
or hexagonal tiles ("Barcelona mode"). Every operation on the pattern wraps around that grid,
so the result tiles seamlessly for both shapes. The finished front is then sampled onto a
cartesian raster over the tile (with the tile outline as mask) for tools and previews.

Deviation from the step order in brief 8.2 (documented): the anisotropy rotation is applied
to the raw raster *before* periodisation, because rotating an already periodic field by an
arbitrary angle destroys its periodicity.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field, replace

import numpy as np
from scipy import ndimage

from . import constants as C
from . import heightfield as hf
from .functional import FunctionalParams, build_functional
from .lattice import Lattice
from .rasterize import RawRaster


@dataclass(frozen=True)
class TileParams:
    macro_depth_mm: float = C.MACRO_DEPTH_DEFAULT_MM
    meso_depth_mm: float = C.MESO_DEPTH_DEFAULT_MM
    macro_meso_cutoff_mm: float = C.MACRO_MESO_CUTOFF_MM
    orientation_mode: str = "auto_along_flow"  # auto_along_flow | cross | none
    functional: FunctionalParams = field(default_factory=FunctionalParams)
    edge_mode: str = "periodic"  # periodic | framed
    texture_period_mm: float = C.DEFAULT_TEXTURE_PERIOD_MM  # square only
    shape: str = "square"  # square | hex ("Barcelona mode")
    tile_size_mm: float = C.TILE_SIZE_MM  # square: side; hex: flat-to-flat
    front_code: bool = True  # emboss the tile code on the front
    material: str = "clay"
    process: str = "press_mould"
    tool_material: str = "pla"
    shrink_pct: float = C.CLAY_SHRINK_DEFAULT_PCT
    printer: str = C.DEFAULT_PRINTER  # internal: build-volume check (largest common bed)
    resolution_px: int = C.INTERNAL_RASTER_PX

    @property
    def lattice(self) -> Lattice:
        return Lattice(self.shape, self.tile_size_mm)

    @property
    def effective_shrink_pct(self) -> float:
        return self.shrink_pct if self.material in ("clay", "loam") else 0.0

    @property
    def tool_scale(self) -> float:
        return 1.0 / (1.0 - self.effective_shrink_pct / 100.0)

    def validate(self) -> list[str]:
        errs = list(self.functional.validate())
        if not 0 <= self.macro_depth_mm <= C.MACRO_DEPTH_MAX_MM:
            errs.append(f"macro depth must be 0-{C.MACRO_DEPTH_MAX_MM} mm")
        if not 0 <= self.meso_depth_mm <= C.MESO_DEPTH_MAX_MM:
            errs.append(f"meso depth must be 0-{C.MESO_DEPTH_MAX_MM} mm")
        if self.orientation_mode not in ("auto_along_flow", "cross", "none"):
            errs.append("orientation_mode must be auto_along_flow, cross or none")
        if self.edge_mode not in ("periodic", "framed"):
            errs.append("edge_mode must be periodic or framed")
        if self.shape not in C.TILE_SHAPES:
            errs.append(f"shape must be one of {C.TILE_SHAPES}")
        if self.tile_size_mm not in C.TILE_SIZES_MM:
            errs.append(f"tile_size_mm must be one of {C.TILE_SIZES_MM}")
        reps = self.tile_size_mm / self.texture_period_mm
        if abs(reps - round(reps)) > 1e-9 or not 1 <= round(reps) <= 4:
            errs.append("texture_period_mm must be the tile size divided by 1-4")
        if self.material not in C.MATERIALS:
            errs.append(f"material must be one of {C.MATERIALS}")
        if self.process not in C.PROCESSES:
            errs.append(f"process must be one of {C.PROCESSES}")
        if self.tool_material not in C.TOOL_MATERIALS:
            errs.append(f"tool_material must be one of {C.TOOL_MATERIALS}")
        if not 0.0 <= self.shrink_pct < 20.0:
            errs.append("shrink_pct must be within 0-20 %")
        if self.printer not in C.PRINTER_PROFILES:
            errs.append(f"printer must be one of {tuple(C.PRINTER_PROFILES)}")
        if self.resolution_px < 64 or self.resolution_px % 2:
            errs.append("resolution_px must be an even number >= 64")
        return errs

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "TileParams":
        d = dict(d)
        fp = dict(d.pop("functional", None) or {})
        size = float(d.get("tile_size_mm", C.TILE_SIZE_MM))
        # pre-0.3 designs stored the channel spacing in mm
        if "channel_spacing_mm" in fp:
            sp = fp.pop("channel_spacing_mm")
            fp.setdefault("channel_count", int(min(4, max(2, round(size / float(sp))))))
        known_f = set(FunctionalParams.__dataclass_fields__)
        known = set(cls.__dataclass_fields__)
        return cls(functional=FunctionalParams(**{k: v for k, v in fp.items() if k in known_f}),
                   **{k: v for k, v in d.items() if k in known})

    def with_updates(self, updates: dict) -> "TileParams":
        merged = self.to_dict()
        for k, v in updates.items():
            if k == "functional" and isinstance(v, dict):
                merged["functional"] = {**merged["functional"], **v}
            else:
                merged[k] = v
        # keep the texture period valid when the size changes
        if "tile_size_mm" in updates and "texture_period_mm" not in updates:
            merged["texture_period_mm"] = merged["tile_size_mm"]
        return TileParams.from_dict(merged)


@dataclass
class Check:
    id: str
    status: str  # pass | warn | fail
    value: float | None
    limit: float | None
    message: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TileResult:
    params: TileParams
    pattern: np.ndarray  # seamless design on the lattice index grid (before edge treatment)
    front: np.ndarray  # finished tile front on a cartesian raster over the tile bbox, mm <= 0
    mask: np.ndarray  # inside the tile outline (cartesian raster)
    macro: np.ndarray
    meso: np.ndarray
    anchor_mask: np.ndarray
    structure_angle_deg: float
    anisotropy: float
    rotation_deg: float
    overhang_fraction: float
    checks: list[Check]
    px_mm: float  # cartesian raster pixel
    code: str | None = None

    @property
    def lattice(self) -> Lattice:
        return self.params.lattice

    @property
    def ok(self) -> bool:
        return all(c.status != "fail" for c in self.checks)

    def heightfield_hash(self) -> str:
        return hashlib.sha256(np.ascontiguousarray(self.front, dtype=np.float32).tobytes()
                              ).hexdigest()


# -- lattice-generic relief operations ----------------------------------------------------
def neighbour_slopes(z: np.ndarray, lat: Lattice) -> np.ndarray:
    """Largest slope angle (deg) to any lattice neighbour (wrapping)."""
    n = z.shape[0]
    worst = np.zeros_like(z)
    for di, dj, vec in lat.step_vectors(n):
        if (di, dj) not in ((1, 0), (0, 1), (1, 1), (1, -1)):
            continue
        d = np.abs(np.roll(np.roll(z, -di, 0), -dj, 1) - z) / float(np.hypot(*vec))
        worst = np.maximum(worst, d)
    return np.degrees(np.arctan(worst))


def limit_slope_lattice(z: np.ndarray, lat: Lattice, max_angle_deg: float,
                        max_iter: int = 10_000) -> np.ndarray:
    """Largest surface <= z whose flanks do not exceed max_angle_deg (cone erosion on the
    lattice grid, wrapping). Only removes tile material, never deepens the relief."""
    if max_angle_deg >= 89.999:
        return z.copy()
    n = z.shape[0]
    s = math.tan(math.radians(max_angle_deg))
    steps = [(di, dj, s * float(np.hypot(*vec))) for di, dj, vec in lat.step_vectors(n)]
    out = z.astype(np.float64, copy=True)
    for _ in range(max_iter):
        cand = out.copy()
        for di, dj, rise in steps:
            np.minimum(cand, np.roll(np.roll(out, di, 0), dj, 1) + rise, out=cand)
        if np.array_equal(cand, out):
            break
        out = cand
    return out


def apply_edge_mode(front: np.ndarray, dist: np.ndarray, edge_mode: str) -> np.ndarray:
    if edge_mode == "periodic":
        chamfer = -(C.EDGE_CHAMFER_MM - dist)
        return np.minimum(front, np.where(dist < C.EDGE_CHAMFER_MM, chamfer, 0.0))
    inner = C.FRAMED_BAND_MM - C.FRAMED_RUNOUT_MM
    # Outer 5 mm of the 10 mm band are flat, relief ramps in over the inner 5 mm.
    return front * np.clip((dist - inner) / C.FRAMED_RUNOUT_MM, 0.0, 1.0)


# -- texture sources ------------------------------------------------------------------------
def _orientation(raw: RawRaster, p: TileParams) -> tuple[np.ndarray, float, float, float]:
    z = hf.detrend(raw.z, C.DETREND_POLY_ORDER)
    raster_fraction = min(0.99, C.RASTER_CROP_FRACTION * np.sqrt(2.0))
    inner = C.RASTER_CROP_FRACTION / raster_fraction
    angle, aniso = hf.dominant_orientation(hf.center_crop(z, inner))
    rot = hf.rotation_for_mode(angle, p.orientation_mode)
    if aniso < C.ANISOTROPY_MIN_FOR_ROTATION:
        rot = 0.0
    return hf.rotate(z, rot), angle, aniso, rot


def _bands(z: np.ndarray, px: float, p: TileParams) -> tuple[np.ndarray, np.ndarray]:
    z = hf.periodic_component(hf.detrend(z, C.DETREND_POLY_ORDER))
    macro, meso = hf.split_bands(z, px, p.macro_meso_cutoff_mm)
    meso = hf.gaussian_lowpass(meso, C.MESO_MIN_WAVELENGTH_MM, px, periodic=True)
    # Moisan makes the field continuous at the seams; the fine band can still kink there.
    return macro, hf.heal_seams(meso)


def texture_from_raster(raw: RawRaster, p: TileParams
                        ) -> tuple[np.ndarray, np.ndarray, float, float, float]:
    """Return (macro, meso, structure_angle, anisotropy, rotation) on the lattice grid."""
    z, angle, aniso, rot = _orientation(raw, p)
    n = p.resolution_px
    lat = p.lattice
    raster_fraction = min(0.99, C.RASTER_CROP_FRACTION * np.sqrt(2.0))
    inner = C.RASTER_CROP_FRACTION / raster_fraction
    if lat.shape == "square":
        z = hf.center_crop(z, inner)
        reps = int(round(p.tile_size_mm / p.texture_period_mm))
        n_period = max(32, int(round(n / reps)))
        macro, meso = _bands(hf.resample(z, n_period), p.texture_period_mm / n_period, p)
        if reps > 1:
            macro, meso = hf.tile_period(macro, reps), hf.tile_period(meso, reps)
        return hf.resample_periodic(macro, n), hf.resample_periodic(meso, n), angle, aniso, rot

    # Hexagon: sample the raw relief on the skew period cell (a parallelogram). Wrapping its
    # index grid is periodicity under the hexagonal lattice.
    n_raw = z.shape[0]
    mm_per_px = p.tile_size_mm / (inner * n_raw)  # same texture scale as a square tile
    b = lat.basis
    corners = [0.5 * (b[:, 0] + b[:, 1]), 0.5 * (b[:, 0] - b[:, 1])]
    r_par = max(float(np.hypot(*c)) for c in corners)
    mm_per_px = max(mm_per_px, r_par / (0.485 * n_raw))  # stay inside the valid raw disc
    c = (np.arange(n) + 0.5) / n - 0.5
    s, t = np.meshgrid(c, c)
    x = s * b[0, 0] + t * b[0, 1]
    y = s * b[1, 0] + t * b[1, 1]
    cols = n_raw / 2 + x / mm_per_px - 0.5
    rows = n_raw / 2 - y / mm_per_px - 0.5
    cell = ndimage.map_coordinates(z, [rows, cols], order=1, mode="nearest")
    macro, meso = _bands(cell, lat.px_mm(n), p)
    return macro, meso, angle, aniso, rot


def procedural_texture(kind: str, lat: Lattice, n: int) -> tuple[np.ndarray, np.ndarray]:
    """Reference textures as functions of x that are periodic under the lattice."""
    if kind == "ref_flat":
        return np.zeros((n, n)), np.zeros((n, n))
    if kind == "ref_geo":
        # Guideline geometry (Mustafa et al. 2021): broad shallow hollows along the flow
        # (vertical), ~75 mm wide -> H/W ~ 0.27 at 20 mm depth; 5 mm grooves every ~15 mm.
        # Wavelengths divide the lattice's x-period, so the field tiles exactly.
        x, _ = lat.grid_points(n)
        period_x = abs(float(lat.basis[0, 0]))
        lam = period_x / max(1, round(period_x / 75.0))
        lam_g = period_x / max(1, round(period_x / 15.0))
        macro = -0.5 * (1.0 + np.cos(2.0 * np.pi * x / lam))
        groove = -np.clip(1.0 - np.abs(((x % lam_g) - lam_g / 2) / 2.5), 0.0, 1.0)
        return macro, groove
    raise ValueError(f"unknown procedural texture {kind!r}")


def run_stage_b(raw: RawRaster, p: TileParams) -> TileResult:
    errs = p.validate()
    if errs:
        raise ValueError("; ".join(errs))
    macro_raw, meso_raw, angle, aniso, rot = texture_from_raster(raw, p)
    return finish_tile(macro_raw, meso_raw, p, angle, aniso, rot)


def run_procedural(kind: str, p: TileParams) -> TileResult:
    """Reference tiles (brief 4.3): REF-FLAT and REF-GEO, no generated sample involved."""
    errs = p.validate()
    if errs:
        raise ValueError("; ".join(errs))
    macro_raw, meso_raw = procedural_texture(kind, p.lattice, p.resolution_px)
    return finish_tile(macro_raw, meso_raw, p, 90.0, 1.0 if kind == "ref_geo" else 0.0, 0.0)


def finish_tile(macro_raw: np.ndarray, meso_raw: np.ndarray, p: TileParams, angle: float,
                aniso: float, rot: float) -> TileResult:
    lat = p.lattice
    n = p.resolution_px
    macro = hf.normalize_depth(macro_raw, p.macro_depth_mm)
    meso = hf.normalize_zero_mean(meso_raw, p.meso_depth_mm)
    texture = macro + meso
    texture -= texture.max()
    depth = -texture.min()
    if depth > C.TOTAL_RELIEF_MAX_MM:
        texture *= C.TOTAL_RELIEF_MAX_MM / depth

    carve_abs, carve_rel, anchor = build_functional(lat, n, p.functional, texture, macro)
    relief = np.minimum(np.minimum(texture + carve_rel, 0.0), carve_abs)
    relief = np.maximum(relief, -C.TOTAL_RELIEF_MAX_MM)  # rills in deep valleys: stay <= 20 mm

    max_angle = C.MAX_FLANK_ANGLE_DEG[p.tool_material]
    overhang = float(np.mean(neighbour_slopes(relief, lat) > max_angle))
    relief = limit_slope_lattice(relief, lat, max_angle)
    if p.functional.template == "diagonal_cascade" and p.functional.anchor_holes:
        hole_floor = -(p.functional.channel_depth_mm + C.ANCHOR_HOLE_DEPTH_MM)
        relief = np.where(anchor, np.minimum(relief, hole_floor), relief)

    # cartesian front over the tile
    if lat.shape == "square":
        front_raw, px = relief, lat.px_mm(n)
        x, y = lat.grid_points(n)
        mask = np.ones_like(relief, dtype=bool)
    else:
        x, y, mask, px = lat.tile_raster(n)
        front_raw = lat.sample(relief, x, y, order=1)
    front = apply_edge_mode(front_raw, lat.edge_distance(x, y), p.edge_mode)
    front = np.where(mask, front, 0.0)
    checks = run_checks(relief, front, mask, anchor, p)
    return TileResult(params=p, pattern=relief, front=front, mask=mask, macro=macro, meso=meso,
                      anchor_mask=anchor, structure_angle_deg=angle, anisotropy=aniso,
                      rotation_deg=rot, overhang_fraction=overhang, checks=checks, px_mm=px)


def wall_field(result: TileResult, m: int, tiles: int = 3) -> tuple[np.ndarray, float]:
    """The seamless pattern over a square window of `tiles` tile sizes (for wall previews).
    Exactly periodic for both lattices (sampled from the lattice grid)."""
    lat = result.lattice
    extent = lat.size * tiles
    px = extent / m
    c = (np.arange(m) + 0.5) * px - extent / 2
    x, y_down = np.meshgrid(c, c)
    cx, cy = lat.tile_center()
    return lat.sample(result.pattern, x + cx, cy - y_down, order=1), px


def joint_lines(lat: Lattice, tiles: int = 3) -> list[list[tuple[float, float]]]:
    """Tile outlines (polylines, mm, centred window) for drawing joints in wall previews."""
    extent = lat.size * tiles
    out = []
    b = lat.basis
    cx, cy = lat.tile_center()
    outline = [(x - cx, y - cy) for x, y in lat.outline()]
    rng = range(-tiles, tiles + 1)
    for i in rng:
        for j in rng:
            ox = i * b[0, 0] + j * b[0, 1]
            oy = i * b[1, 0] + j * b[1, 1]
            if abs(ox) > extent * 0.75 or abs(oy) > extent * 0.75:
                continue
            out.append([(x + ox, y + oy) for x, y in outline + outline[:1]])
    return out


# -- tile code on the front ------------------------------------------------------------------
def code_mask(text: str, px_mm: float) -> np.ndarray:
    """Raster of the code text (True = letter), cap height FRONT_CODE_HEIGHT_MM."""
    from PIL import Image, ImageDraw, ImageFont

    size_px = max(12, int(round(C.FRONT_CODE_HEIGHT_MM / 0.72 / px_mm)))
    font = ImageFont.load_default(size=size_px)
    stroke = max(1, int(round(0.12 / px_mm)))  # thicker strokes: >= ~0.9 mm for FDM + clay
    x0, t, r, b = ImageDraw.Draw(Image.new("L", (1, 1))).textbbox((0, 0), text, font=font,
                                                                    stroke_width=stroke)
    im = Image.new("L", (r - x0 + 4, b - t + 4), 0)
    ImageDraw.Draw(im).text((2 - x0, 2 - t), text, fill=255, font=font, stroke_width=stroke,
                            stroke_fill=255)
    return np.asarray(im) > 127


def stamp_front_code(result: TileResult, text: str) -> TileResult:
    """Emboss the tile code into a small flattened field near the bottom-right edge.

    The field is blended into the relief over 3 mm; the letters are 1 mm deep in the tile
    (raised on the matrix). This is the only place where the pattern is not seamless.
    """
    p = result.params
    if not p.front_code or not text:
        return result
    lat, px = result.lattice, result.px_mm
    letters = code_mask(text, px)
    h, w = letters.shape
    ny, nx = result.front.shape
    margin = int(round(C.FRONT_CODE_MARGIN_MM / px))
    if lat.shape == "square":
        r0, c0 = ny - margin - h, nx - margin - w
    else:  # just above the flat bottom edge, right of the centre
        r0 = ny - margin - h
        c0 = int(round(nx / 2 + (C.FRONT_CODE_MARGIN_MM / px)))
    # keep the field inside the raster (coarse preview rasters, small tiles)
    r0 = int(min(max(0, r0), max(0, ny - h)))
    c0 = int(min(max(0, c0), max(0, nx - w)))
    h, w = min(h, ny - r0), min(w, nx - c0)
    letters = letters[:h, :w]
    pad = int(round(2.0 / px))
    blend = int(round(3.0 / px))
    zone = np.zeros((ny, nx), dtype=bool)
    zone[max(0, r0 - pad):r0 + h + pad, max(0, c0 - pad):c0 + w + pad] = True
    front = result.front.copy()
    plane = float(np.median(front[zone])) if zone.any() else 0.0
    d = ndimage.distance_transform_edt(~zone) * px
    wgt = np.clip(1.0 - d / (blend * px), 0.0, 1.0)
    wgt = wgt * wgt * (3 - 2 * wgt)
    front = front * (1 - wgt) + plane * wgt
    text_full = np.zeros((ny, nx), dtype=bool)
    text_full[r0:r0 + h, c0:c0 + w] = letters
    front = np.where(text_full & result.mask, front - C.FRONT_CODE_DEPTH_MM, front)
    front = np.where(result.mask, front, 0.0)
    checks = [c for c in result.checks if c.id != "min_thickness"]
    checks.insert(2, _min_thickness_check(front, result.mask, p))
    return replace(result, front=front, checks=checks, code=text)


# -- checks ----------------------------------------------------------------------------------
def _min_thickness_check(front: np.ndarray, mask: np.ndarray, p: TileParams) -> Check:
    min_t = C.MIN_MATERIAL_THICKNESS_MM[p.material]
    remaining = C.TILE_THICKNESS_MM + float(front[mask].min())
    return Check("min_thickness", "pass" if remaining >= min_t else "fail", round(remaining, 2),
                 min_t, "Material left under the deepest relief point.")


def run_checks(pattern: np.ndarray, front: np.ndarray, mask: np.ndarray, anchor: np.ndarray,
               p: TileParams) -> list[Check]:
    lat = p.lattice
    checks: list[Check] = []
    # Periodicity on the lattice grid: no step and no crease where tiles meet.
    seam = hf.seam_ratio(pattern)
    crease = hf.seam_curvature_ratio(pattern)
    tol = 2.0
    ok = seam <= tol and crease <= tol
    checks.append(Check("periodicity", "pass" if ok else "fail", round(max(seam, crease), 3), tol,
                        "Opposite edges continue seamlessly: no step and no crease at the joint."))
    # Demouldability: max flank angle outside the intentional anchor holes.
    max_angle = C.MAX_FLANK_ANGLE_DEG[p.tool_material]
    slopes = neighbour_slopes(pattern, lat)
    near_anchor = _dilate(anchor, 3)
    worst = float(slopes[~near_anchor].max()) if (~near_anchor).any() else 0.0
    checks.append(Check("draft", "pass" if worst <= max_angle + 0.5 else "fail", round(worst, 2),
                        max_angle, "Maximum flank angle for a rigid tool (anchor holes excluded)."))
    checks.append(_min_thickness_check(front, mask, p))
    relief_depth = -float(np.percentile(pattern[~anchor] if (~anchor).any() else pattern, 0.1))
    checks.append(Check("relief_depth", "pass" if relief_depth <= C.TOTAL_RELIEF_MAX_MM + 0.01
                        else "warn", round(relief_depth, 2), C.TOTAL_RELIEF_MAX_MM,
                        "Relief depth within the 20 mm guideline (Mustafa et al. 2021)."))
    if p.material == "loam":
        checks.append(Check("material_outdoor", "warn", None, None,
                            "Unfired clay is not rain-proof: indoor / covered use only."))
    return checks


def _dilate(mask: np.ndarray, it: int) -> np.ndarray:
    if not mask.any():
        return mask
    return ndimage.binary_dilation(mask, iterations=it)


def design_json(result: TileResult, extra: dict | None = None) -> str:
    doc = {
        "pipeline_version": C.PIPELINE_VERSION,
        "interface_version": C.INTERFACE_VERSION,
        "params": result.params.to_dict(),
        "code": result.code,
        "heightfield_sha256": result.heightfield_hash(),
        "structure_angle_deg": result.structure_angle_deg,
        "anisotropy": result.anisotropy,
        "rotation_deg": result.rotation_deg,
        "checks": [c.to_dict() for c in result.checks],
        "license": "CC-BY-SA-4.0",
    }
    if extra:
        doc.update(extra)
    return json.dumps(doc, indent=2, sort_keys=True, default=float)


__all__ = ["TileParams", "TileResult", "Check", "run_stage_b", "run_procedural",
           "stamp_front_code", "design_json", "replace"]
