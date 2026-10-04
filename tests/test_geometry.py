"""Mandatory geometry tests (brief 13.3)."""

import numpy as np
import pytest
from biotile_geometry import constants as C
from biotile_geometry import heightfield as hf
from biotile_geometry.pipeline import TileParams, run_stage_b
from biotile_geometry.tools import (
    ToolFrame,
    build_frame_walls,
    build_matrix,
    build_toolset,
    hanging_channel_clearance_mm,
)
from scipy import ndimage

FAST = dict(resolution_px=256)


# --- periodicity ----------------------------------------------------------------------
def test_moisan_periodic_component_is_seamless():
    rng = np.random.default_rng(0)
    yy, xx = np.mgrid[0:128, 0:128]
    z = 0.05 * xx + 0.02 * yy + rng.normal(0, 0.1, (128, 128))  # strong ramp -> seams
    assert hf.seam_ratio(z) > 20
    assert hf.seam_ratio(hf.periodic_component(z)) < 2.0


@pytest.mark.parametrize("period", [150.0, 75.0, 50.0])
def test_tile_pattern_is_periodic(raw_bark, period):
    r = run_stage_b(raw_bark, TileParams(texture_period_mm=period, **FAST))
    assert hf.seam_ratio(r.pattern) < 2.0
    assert next(c for c in r.checks if c.id == "periodicity").status == "pass"


@pytest.mark.parametrize("shape", ["square", "hex"])
@pytest.mark.parametrize("template", ["diagonal_cascade", "moss_nests"])
def test_functional_layer_is_seamless(raw_bark, shape, template):
    p = TileParams(**FAST).with_updates({"shape": shape, "functional": {"template": template}})
    r = run_stage_b(raw_bark, p)
    assert hf.seam_ratio(r.pattern) < 2.0 and hf.seam_curvature_ratio(r.pattern) < 2.0


def test_diagonal_channels_tile_exactly():
    from biotile_geometry.functional import FunctionalParams, diagonal_channels
    from biotile_geometry.lattice import Lattice

    for k in (2, 3, 4):
        lat = Lattice("square", 150.0)
        carve, anchor = diagonal_channels(lat, 300, FunctionalParams(template="diagonal_cascade", channel_count=k))
        big, big_anchor = diagonal_channels(Lattice("square", 300.0), 600,
                                            FunctionalParams(template="diagonal_cascade", channel_count=2 * k))
        assert np.allclose(big[:300, :300], big[300:, 300:])
        assert np.allclose(big[:300, :300], carve)


def test_hex_lattice_sampling_is_periodic():
    from biotile_geometry.lattice import Lattice

    lat = Lattice("hex", 150.0)
    rng = np.random.default_rng(3)
    field = ndimage.gaussian_filter(rng.normal(size=(128, 128)), 4, mode="wrap")
    x = rng.uniform(-100, 100, 500)
    y = rng.uniform(-100, 100, 500)
    v0 = lat.sample(field, x, y)
    for k in range(2):  # translation by either lattice vector gives the same value
        bx, by = lat.basis[:, k]
        assert np.allclose(lat.sample(field, x + bx, y + by), v0, atol=1e-9)


def test_channel_count_must_divide_tile(raw_bark):
    p = TileParams(**FAST).with_updates({"functional": {"template": "diagonal_cascade",
                                                        "channel_count": 5}})
    with pytest.raises(ValueError, match="divide"):
        run_stage_b(raw_bark, p)


def test_old_designs_with_channel_spacing_still_load():
    p = TileParams.from_dict({"functional": {"template": "diagonal_cascade", "channel_spacing_mm": 50.0}})
    assert p.functional.channel_count == 3


# --- watertightness -------------------------------------------------------------------
def test_all_exported_meshes_are_watertight(raw_bark):
    r = run_stage_b(raw_bark, TileParams(**FAST))
    ts = build_toolset(r, grid_mm=1.0)
    assert set(ts.parts) >= {"matrix", "frame_top", "frame_bottom", "frame_left", "frame_right",
                             "backplate", "hole_punch"}
    for name, mesh in ts.parts.items():
        assert mesh.is_watertight, name
        assert mesh.volume > 0, name


def test_half_channel_walls_watertight():
    walls = build_frame_walls(TileParams(**FAST), channels="edge_half")
    assert all(m.is_watertight for m in walls.values())


# --- minimum material thickness -------------------------------------------------------
@pytest.mark.parametrize("material", ["clay", "concrete"])
def test_minimum_thickness(raw_bark, material):
    r = run_stage_b(raw_bark, TileParams(material=material, macro_depth_mm=20, meso_depth_mm=5,
                                         **FAST))
    check = next(c for c in r.checks if c.id == "min_thickness")
    remaining = C.TILE_THICKNESS_MM + float(r.front.min())
    assert check.value == pytest.approx(remaining, abs=0.01)
    assert remaining >= C.MIN_MATERIAL_THICKNESS_MM[material]
    assert check.status == "pass"


def test_total_relief_respects_guideline(raw_bark):
    p = TileParams(macro_depth_mm=20, meso_depth_mm=5, **FAST).with_updates(
        {"functional": {"template": "none"}})
    r = run_stage_b(raw_bark, p)
    assert -r.pattern.min() <= C.TOTAL_RELIEF_MAX_MM + 1e-6


# --- flank angle ----------------------------------------------------------------------
def test_limit_slope_enforces_max_angle():
    rng = np.random.default_rng(1)
    z = -np.abs(rng.normal(0, 5, (96, 96)))
    px = 0.2
    out = hf.limit_slope(z, px, 85.0)
    assert np.all(out <= z + 1e-12)  # only removes tile material
    s = math_slopes(out, px)
    assert s.max() <= np.tan(np.radians(85.0)) * 1.0001


def math_slopes(z, px):
    """Largest one-sided neighbour slope (x and y), matching the erosion stencil."""
    dx = np.abs(np.roll(z, -1, axis=1) - z) / px
    dy = np.abs(np.roll(z, -1, axis=0) - z) / px
    return np.maximum(dx, dy)


@pytest.mark.parametrize("tool", ["pla", "silicone"])
def test_draft_check(raw_bark, tool):
    r = run_stage_b(raw_bark, TileParams(tool_material=tool, **FAST))
    check = next(c for c in r.checks if c.id == "draft")
    assert check.status == "pass"
    assert check.value <= C.MAX_FLANK_ANGLE_DEG[tool] + 0.5


# --- build volume ---------------------------------------------------------------------
def test_bed_fit_180_at_default_shrink(raw_bark):
    r = run_stage_b(raw_bark, TileParams(**FAST))
    ts = build_toolset(r, grid_mm=1.0)
    assert all(v["fits_180"] for v in ts.bed_checks.values()), ts.bed_checks


def test_bed_fit_high_shrink_needs_larger_printer(raw_bark):
    from biotile_geometry.tools import bed_check

    r = run_stage_b(raw_bark, TileParams(shrink_pct=12.0, **FAST))
    bed = build_toolset(r, grid_mm=1.0).bed_checks
    assert not bed["matrix"]["fits_180"] and bed["matrix"]["fits"]
    assert bed_check(bed).status == "warn"


@pytest.mark.parametrize("shape", ["square", "hex"])
def test_all_parts_watertight_for_both_shapes(raw_bark, shape):
    r = run_stage_b(raw_bark, TileParams(**FAST).with_updates({"shape": shape}))
    ts = build_toolset(r, grid_mm=1.5)
    assert all(m.is_watertight and m.volume > 0 for m in ts.parts.values())
    if shape == "hex":
        assert {"frame_upper", "frame_lower"} <= set(ts.parts)


# --- shrinkage ------------------------------------------------------------------------
@pytest.mark.parametrize("shrink", [0.0, 8.0, 10.0, 12.0])
def test_shrinkage_back_calculation(raw_bark, shrink):
    p = TileParams(shrink_pct=shrink, **FAST)
    r = run_stage_b(raw_bark, p)
    m = build_matrix(r, grid_mm=1.0)
    plinth = m.extents[0] - 2 * C.REGISTRATION_FLANGE_MM
    fired = plinth * (1 - shrink / 100.0)
    assert fired == pytest.approx(C.TILE_SIZE_MM, abs=0.01)
    fr = ToolFrame.from_params(p)
    assert fr.wall_h - C.MATRIX_PLINTH_MM == pytest.approx(C.TILE_THICKNESS_MM / (1 - shrink / 100))


def test_concrete_has_no_shrinkage():
    assert TileParams(material="concrete", shrink_pct=10.0).tool_scale == 1.0


# --- hanging points vs channels -------------------------------------------------------
def test_hanging_points_do_not_intersect_channels():
    p = TileParams(**FAST)
    assert hanging_channel_clearance_mm(p, "none") > 0
    assert hanging_channel_clearance_mm(p, "edge_half") > 0


# --- determinism ----------------------------------------------------------------------
def test_determinism_same_input_same_hash():
    from biotile_geometry.rasterize import load_mesh, rasterize_mesh
    from conftest import FIXTURES

    mesh = load_mesh(FIXTURES / "synthetic_karren.glb")
    hashes = []
    for _ in range(2):
        raw = rasterize_mesh(mesh, 256, seed=42)
        hashes.append(run_stage_b(raw, TileParams(**FAST)).heightfield_hash())
    assert hashes[0] == hashes[1]


def test_orientation_estimate():
    x = np.arange(256)
    stripes = np.tile(np.sin(2 * np.pi * x / 16), (256, 1))
    angle, aniso = hf.dominant_orientation(stripes)
    assert angle == pytest.approx(90.0, abs=1.0) and aniso > 0.9
    assert hf.rotation_for_mode(0.0, "auto_along_flow") in (90.0, -90.0)
    assert hf.rotation_for_mode(90.0, "auto_along_flow") == 0.0


def test_along_flow_rotation_makes_structures_vertical(raw_bark):
    r = run_stage_b(raw_bark, TileParams(**FAST))
    angle, aniso = hf.dominant_orientation(r.macro + r.meso)
    assert aniso > 0.3
    assert abs(angle - 90.0) < 10.0


def test_no_crease_at_the_joint(raw_bark):
    """Seams must be smooth, not only continuous: no kink visible in raking light."""
    p = TileParams(**FAST).with_updates({"functional": {"template": "none"}})
    r = run_stage_b(raw_bark, p)
    assert hf.seam_curvature_ratio(r.pattern) < 1.5


def test_moss_nests_prefer_natural_hollows(raw_tafoni):
    from biotile_geometry.functional import FunctionalParams, place_nests

    p = TileParams(**FAST).with_updates({"functional": {"template": "none"}})
    r = run_stage_b(raw_tafoni, p)
    pts = place_nests(p.lattice, p.resolution_px, FunctionalParams(), r.macro)
    assert len(pts) >= 6
    # the first nests sit in the deepest third of the macro relief
    x, y = p.lattice.grid_points(p.resolution_px)
    first = pts[:3]
    depths = [r.macro[np.unravel_index(np.argmin((x - px) ** 2 + (y - py) ** 2), x.shape)]
              for px, py in first]
    assert np.mean(depths) < np.percentile(r.macro, 35)


def test_front_code_is_stamped_and_rest_untouched(raw_bark):
    from biotile_geometry.pipeline import stamp_front_code

    r = run_stage_b(raw_bark, TileParams(resolution_px=512))
    s = stamp_front_code(r, "BT-4S1984")
    changed = np.abs(s.front - r.front) > 1e-9
    assert changed.any() and s.code == "BT-4S1984"
    rows, cols = np.nonzero(changed)
    # only a small field near the bottom-right corner changes
    assert rows.min() > 0.75 * r.front.shape[0] and cols.min() > 0.5 * r.front.shape[1]
    off = TileParams(resolution_px=512, front_code=False)
    assert stamp_front_code(run_stage_b(raw_bark, off), "BT-4S1984").code is None


@pytest.mark.parametrize("shape,size", [("square", 100.0), ("square", 150.0), ("hex", 150.0), ("hex", 100.0)])
def test_hanging_pads_inside_tile(shape, size):
    from biotile_geometry.lattice import Lattice

    p = TileParams(**FAST).with_updates({"shape": shape, "tile_size_mm": size, "shrink_pct": 0.0})
    fr = ToolFrame.from_params(p)
    lat = Lattice(shape, size)
    cx, cy = lat.tile_center()
    for x, y in fr.hanging_points():
        d = lat.edge_distance(np.array(cx - x), np.array(cy + y))
        assert d >= C.HANG_PAD_DIAMETER_MM / 2, (shape, size, x, y, d)
