"""Surface metrics (brief 8.5) on the internal high-resolution height field.

ISO 25178 parameters come from surfalize (pinned in pyproject; early project with an
unstable API, so every call is wrapped and failures are reported, not hidden).
Assumption documented for the dataset: printing transfers waviness well, fine roughness
poorly (PLOS ONE 2019: Smr more robust than Sa/Sv in replicated topographies).
"""

from __future__ import annotations

import math
import warnings

import numpy as np
from scipy import ndimage

from . import constants as C
from . import heightfield as hf

ISO_PARAMS = ("Sa", "Sq", "Sz", "Sp", "Sv", "Ssk", "Sku", "Sdr", "Sdq", "Smr", "Sk", "Spk", "Svk")
SMR_C_MM = 1.0
_METRIC_PX = 512  # surfalize is slow on 2048^2; metrics are evaluated on a 0.29 mm grid


def _iso(z: np.ndarray, px_mm: float) -> dict[str, float | None]:
    # Flat references (REF-FLAT) make several parameters undefined: report None, stay quiet.
    with warnings.catch_warnings(), np.errstate(all="ignore"):
        warnings.simplefilter("ignore")
        return _iso_inner(z, px_mm)


def _iso_inner(z: np.ndarray, px_mm: float) -> dict[str, float | None]:
    from surfalize import Surface

    # surfalize expects micrometres for step and height; we keep mm and convert.
    surf = Surface(z * 1000.0, px_mm * 1000.0, px_mm * 1000.0)
    out: dict[str, float | None] = {}
    for name in ISO_PARAMS:
        try:
            # Smr needs a height: we report Smr(c = 1 mm), material ratio 1 mm below the top.
            v = float(surf.Smr(SMR_C_MM * 1000.0) if name == "Smr" else getattr(surf, name)())
            if name in ("Sa", "Sq", "Sz", "Sp", "Sv", "Sk", "Spk", "Svk"):
                v /= 1000.0  # back to mm
            out[name] = v if math.isfinite(v) else None
        except Exception:  # noqa: BLE001 - report as missing, see module docstring
            out[name] = None
    return out


def pocket_volume_per_area(z: np.ndarray, px_mm: float) -> float:
    """Water that the relief can hold when held vertically is not trivially defined; as a
    proxy we use the volume enclosed below the morphological closing with a 20 mm disk
    (pockets narrower than the disk), in mm^3 per mm^2 (= mm)."""
    r = int(round(10.0 / px_mm))
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    disk = xx**2 + yy**2 <= r * r
    closed = ndimage.grey_closing(z, footprint=disk, mode="wrap")
    return float(np.mean(closed - z))


def crevice_width_distribution(z: np.ndarray, px_mm: float) -> dict[str, float]:
    """Area share of recesses (>= 1 mm below local surroundings) per hypothesis width class,
    using the local width = 2 x distance to the recess border (medial-axis estimate)."""
    smooth = ndimage.uniform_filter(z, size=max(3, int(round(20.0 / px_mm))), mode="wrap")
    recess = (smooth - z) >= 1.0
    if not recess.any():
        return {k: 0.0 for k in C.CREVICE_CLASSES_MM}
    width = 2.0 * ndimage.distance_transform_edt(recess) * px_mm
    out = {}
    for name, (lo, hi) in C.CREVICE_CLASSES_MM.items():
        out[name] = float(np.mean((width >= lo) & (width <= hi) & recess))
    return out


def macro_hollow_hw(macro: np.ndarray, px_mm: float) -> float | None:
    """Mean depth/width ratio of macro hollows (Mustafa et al. 2021 target: 0.2-0.3).

    Hollows = connected regions below the median of the macro band; width = equivalent
    circle diameter, depth = median minus region minimum.
    """
    med = float(np.median(macro))
    labels, n = ndimage.label(macro < med)
    if n == 0:
        return None
    idx = np.arange(1, n + 1)
    areas = ndimage.sum_labels(np.ones_like(macro), labels, idx) * px_mm**2
    mins = ndimage.minimum(macro, labels, idx)
    keep = areas >= 100.0  # ignore specks < 1 cm2
    if not keep.any():
        return None
    widths = 2.0 * np.sqrt(areas[keep] / np.pi)
    depths = med - np.asarray(mins)[keep]
    return float(np.average(depths / widths, weights=areas[keep]))


def _metric_field(result) -> tuple[np.ndarray, np.ndarray, float, bool]:
    """(field, macro, px, periodic). Square: the periodic pattern. Hexagon: the largest
    centred square inside the tile front (cartesian, not periodic)."""
    lat = result.lattice
    if lat.shape == "square":
        z = hf.resample_periodic(result.pattern, _METRIC_PX)
        macro = hf.resample_periodic(result.macro, _METRIC_PX)
        return z, macro, lat.size / _METRIC_PX, True
    ny, nx = result.front.shape
    side = int((lat.size / 2) * 2 / np.sqrt(2) / result.px_mm) // 2 * 2
    r0, c0 = (ny - side) // 2, (nx - side) // 2
    z = result.front[r0:r0 + side, c0:c0 + side]
    zc = hf.resample(z, _METRIC_PX)
    px = side * result.px_mm / _METRIC_PX
    return zc, hf.gaussian_lowpass(zc, C.MACRO_MESO_CUTOFF_MM, px, periodic=False), px, False


def compute_metrics(result) -> dict:
    from .functional import flow_path_length_mm

    p = result.params
    z, macro, px, periodic = _metric_field(result)
    metrics: dict = {"grid_mm": round(px, 4), "iso25178": _iso(z, px), "scale_separated": {},
                     "shape": p.shape, "tile_size_mm": p.tile_size_mm}
    for cutoff in C.METRIC_CUTOFFS_MM:
        low = hf.gaussian_lowpass(z, cutoff, px, periodic=periodic)
        rough = z - low
        metrics["scale_separated"][f"{cutoff:g}mm"] = {
            "Sa": float(np.mean(np.abs(rough - rough.mean()))),
            "Sq": float(np.std(rough)),
        }
    angle, aniso = hf.dominant_orientation(z)
    metrics.update({
        "pocket_volume_per_area_mm": pocket_volume_per_area(z, px),
        "anisotropy_index": aniso,
        "main_direction_deg": angle,
        "overhang_fraction_before_draft": result.overhang_fraction,
        "crevice_share": crevice_width_distribution(z, px),
        "flow_path_length_mm": flow_path_length_mm(result.lattice, p.functional),
        "relief_depth_mm": float(-z.min()),
        "macro_hollow_hw": macro_hollow_hw(macro, px),
    })
    return metrics
