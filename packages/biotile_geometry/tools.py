"""Printable tool set (brief 5.2) for square and hexagonal tiles.

Parts: matrix/stamp (relief on a plinth, registration flange and pins), casting frame
(square: four walls; hexagon: two halves of three walls each), back plate, hole punch.

Casting coordinate frame (all parts are modelled in place, then laid flat for export):
    The matrix lies relief-up on the table, centred on the tile centre. The tile is cast face
    down, so tile x is mirrored about the centre; y (towards the tile's top edge) is kept.
    z = 0 is the table; the flange top is at MATRIX_BASE_MM; the tile's reference plane sits
    on the plinth top at z_front = MATRIX_BASE_MM + MATRIX_PLINTH_MM.

Hanging (option a, 2026-10-03): the back plate presses two flat, solid pads and carries two
guide bores tilted HANG_HOLE_ANGLE_DEG upwards; the printed punch makes the slanted blind
holes in leather-hard clay. The tile hangs on two stainless pins of the wall adapter.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import trimesh
from manifold3d import CrossSection, JoinType, Manifold
from scipy import ndimage

from . import constants as C
from .lattice import Lattice
from .mesh import (
    box,
    cylinder_z,
    decimate,
    footprint_fits,
    from_manifold,
    heightfield_solid,
    to_manifold,
)
from .pipeline import Check, TileParams, TileResult


@dataclass
class ToolFrame:
    lat: Lattice  # fired-size lattice
    s: float  # tool scale (clay shrinkage)
    z_front: float
    wall_h: float
    c: float = C.FIT_CLEARANCE_MM
    T: float = C.FRAME_WALL_THICKNESS_MM
    F: float = C.REGISTRATION_FLANGE_MM

    @classmethod
    def from_params(cls, p: TileParams) -> "ToolFrame":
        s = p.tool_scale
        return cls(lat=p.lattice, s=s, z_front=C.MATRIX_BASE_MM + C.MATRIX_PLINTH_MM,
                   wall_h=C.MATRIX_PLINTH_MM + C.TILE_THICKNESS_MM * s)

    @property
    def S(self) -> float:  # noqa: N802 - scaled tile size (square side / hex flat-to-flat)
        return self.lat.size * self.s

    def outline(self, offset: float = 0.0) -> CrossSection:
        """Scaled tile outline in casting coordinates (centred, mirrored), grown by offset."""
        cx, cy = self.lat.tile_center()
        pts = [((cx - x) * self.s, (y - cy) * self.s) for x, y in self.lat.outline()]
        cs = CrossSection([pts[::-1]])  # mirroring flips the orientation; reverse to CCW
        if offset:
            cs = cs.offset(offset, JoinType.Miter)
        return cs

    def prism(self, offset: float, z0: float, z1: float) -> Manifold:
        return Manifold.extrude(self.outline(offset), z1 - z0).translate([0.0, 0.0, z0])

    def pin_centers(self) -> list[tuple[float, float]]:
        """Registration pins in the flange ring, under the frame walls."""
        o = self.F - C.REGISTRATION_PIN_DIAMETER_MM / 2 - C.FIT_CLEARANCE_MM
        if self.lat.shape == "square":
            h = self.S / 2
            return [(-h - o, -h - o), (h + o, -h - o), (-h - o, h + o), (h + o, h + o)]
        # hexagon: in the flange ring outside each edge midpoint (under the frame walls)
        r = self.S / 2 + o
        return [(r * math.cos(math.radians(a)), r * math.sin(math.radians(a)))
                for a in (30, 90, 150, 210, 270, 330)]

    def hanging_points(self) -> list[tuple[float, float]]:
        """Hole positions in casting coordinates (symmetric, so mirroring is moot)."""
        size = self.lat.size
        if self.lat.shape == "square":
            spacing = min(C.HANGING_POINT_SPACING_MM, size - 50.0)
        else:
            spacing = C.HEX_HANGING_POINT_SPACING_MM * size / C.TILE_SIZE_MM
        y_t = size / 2 - C.HANGING_POINT_BELOW_TOP_MM  # from the tile centre (fired mm)
        half_t = spacing / 2
        # small tiles: move the pads inwards until each keeps 1 mm to the outline
        need = C.HANG_PAD_DIAMETER_MM / 2 + 1.0
        cx, cy = self.lat.tile_center()
        while half_t > need and float(self.lat.edge_distance(np.array(cx + half_t),
                                                            np.array(cy + y_t))) < need:
            half_t -= 0.5
        return [(-half_t * self.s, y_t * self.s), (half_t * self.s, y_t * self.s)]


def _sample_front(result: TileResult, fr: ToolFrame, n_x: int, n_y: int, dx: float,
                  x0: float, y0: float) -> np.ndarray:
    """Front height (fired mm) at matrix node positions (casting coords, mirrored)."""
    lat = result.lattice
    cx, cy = lat.tile_center()
    xs = x0 + np.arange(n_x) * dx
    ys = y0 + (n_y - 1 - np.arange(n_y)) * dx  # row 0 = max y
    xm, ym = np.meshgrid(xs, ys)
    xt = cx - xm / fr.s  # mirror back to tile coordinates
    yt = cy + ym / fr.s
    w, h = lat.bbox
    off_x = 0.0 if lat.shape == "square" else -w / 2
    off_y = 0.0 if lat.shape == "square" else -h / 2
    px = result.px_mm
    cols = (xt - off_x) / px - 0.5
    rows = (h + off_y - yt) / px - 0.5
    return ndimage.map_coordinates(result.front, [rows, cols], order=1, mode="nearest")


def build_matrix(result: TileResult, grid_mm: float = C.EXPORT_GRID_MM,
                 max_faces: int = C.EXPORT_MAX_TRIANGLES) -> trimesh.Trimesh:
    """Matrix / stamp: relief on a plinth (tile outline), registration flange and pins."""
    fr = ToolFrame.from_params(result.params)
    w, h = fr.lat.bbox
    w, h = w * fr.s + 1.0, h * fr.s + 1.0  # a little margin around the outline
    n_x = int(math.ceil(w / grid_mm)) + 1
    n_y = int(math.ceil(h / grid_mm)) + 1
    dx = max(w / (n_x - 1), h / (n_y - 1))
    x0, y0 = -(n_x - 1) * dx / 2, -(n_y - 1) * dx / 2
    front = _sample_front(result, fr, n_x, n_y, dx, x0, y0)
    top = fr.z_front - np.minimum(front, 0.0) * fr.s  # recess in the tile = bump on the matrix
    relief = heightfield_solid(top, x0, y0, dx, z_bottom=0.5)
    relief = decimate(relief, max_faces - 4_000)
    plinth = to_manifold(relief) ^ fr.prism(0.0, 0.0, fr.z_front + 40.0)
    parts = plinth + fr.prism(fr.F, 0.0, C.MATRIX_BASE_MM)
    r = C.REGISTRATION_PIN_DIAMETER_MM / 2
    for cx, cy in fr.pin_centers():
        parts = parts + cylinder_z(cx, cy, C.MATRIX_BASE_MM - 0.1,
                                   C.MATRIX_BASE_MM + C.REGISTRATION_PIN_HEIGHT_MM, r)
    return from_manifold(parts)


def _rod_along_y(x: float, z: float, y0: float, y1: float, r: float) -> Manifold:
    cyl = Manifold.cylinder(y1 - y0, r, r, 48)
    return cyl.rotate([-90.0, 0.0, 0.0]).translate([x, y0, z])


def _edge_ribs(fr: ToolFrame) -> tuple[Manifold, Manifold]:
    """Collecting-groove rib (top inner face) and drip-groove rib (bottom inner face)."""
    s, c = fr.s, fr.c
    h = fr.S / 2
    half_w = (fr.S / 2 if fr.lat.shape == "square" else fr.lat.side * s / 2) + c
    g_c = fr.z_front + C.COLLECTING_GROOVE_CENTER_BEHIND_FRONT_MM * s
    g_w = C.COLLECTING_GROOVE_WIDTH_MM * s
    top = box(-half_w, h + c - C.COLLECTING_GROOVE_DEPTH_MM * s, g_c - g_w / 2, half_w, h + c + 0.1,
              g_c + g_w / 2)
    d0 = fr.z_front + C.DRIP_GROOVE_BEHIND_FRONT_MM * s
    d = C.DRIP_GROOVE_SIZE_MM * s
    bottom = box(-half_w, -h - c - 0.1, d0, half_w, -h - c + d, d0 + d)
    return top, bottom


def _pin_holes(fr: ToolFrame) -> list[Manifold]:
    r = C.REGISTRATION_PIN_DIAMETER_MM / 2 + C.FIT_CLEARANCE_MM
    z0 = C.MATRIX_BASE_MM
    return [cylinder_z(x, y, z0 - 1, z0 + C.REGISTRATION_PIN_HEIGHT_MM + 0.5, r)
            for x, y in fr.pin_centers()]


def build_frame_walls(p: TileParams, channels: str = "none") -> dict[str, trimesh.Trimesh]:
    fr = ToolFrame.from_params(p)
    if fr.lat.shape == "hex":
        return _hex_frame(fr)
    return _square_frame(fr, channels)


def _square_frame(fr: ToolFrame, channels: str) -> dict[str, trimesh.Trimesh]:
    """Top/bottom walls span the corners and hold the pin holes; side walls slide in with
    full-height tenons."""
    h, c, T, s = fr.S / 2, fr.c, fr.T, fr.s
    z0, z1 = C.MATRIX_BASE_MM, C.MATRIX_BASE_MM + fr.wall_h
    tw, td = C.FRAME_TENON_MM
    side_x = [-h - c - T / 2, h + c + T / 2]
    rib_top, rib_bottom = _edge_ribs(fr)
    holes = _pin_holes(fr)

    def slots(y_face: float, direction: float) -> list[Manifold]:
        out = []
        for xc in side_x:
            ya, yb = sorted([y_face, y_face + direction * (td + c)])
            out.append(box(xc - tw / 2 - c / 2, ya, z0 - 1, xc + tw / 2 + c / 2, yb, z1 + 1))
        return out

    top = box(-h - c - T, h + c, z0, h + c + T, h + c + T, z1) + rib_top
    for cut in slots(h + c, +1) + holes:
        top = top - cut
    bottom = box(-h - c - T, -h - c - T, z0, h + c + T, -h - c, z1) + rib_bottom
    for cut in slots(-h - c, -1) + holes:
        bottom = bottom - cut
    walls = {"frame_top": top, "frame_bottom": bottom}
    for name, x_in, x_out in (("frame_left", -h - c, -h - c - T), ("frame_right", h + c, h + c + T)):
        xa, xb = sorted([x_in, x_out])
        wall = box(xa, -h - c, z0, xb, h + c, z1)
        xc = (xa + xb) / 2
        wall = wall + box(xc - tw / 2, h + c - 0.1, z0, xc + tw / 2, h + c + td, z1)
        wall = wall + box(xc - tw / 2, -h - c - td, z0, xc + tw / 2, -h - c + 0.1, z1)
        if channels == "edge_half":
            r = C.HALF_CHANNEL_DIAMETER_MM * s / 2
            zc = fr.z_front + C.HALF_CHANNEL_CENTER_BEHIND_FRONT_MM * s
            wall = wall + _rod_along_y(x_in, zc, -h - c, h + c, r)
        walls[name] = wall
    return {k: from_manifold(v) for k, v in walls.items()}


def _hex_frame(fr: ToolFrame) -> dict[str, trimesh.Trimesh]:
    """Hexagonal ring split through the left/right corners into an upper and a lower half
    (three walls each). Each half is pulled straight up / down: every wall normal has a
    positive component in that direction, so nothing scrapes. Pins hold it on the flange."""
    z0, z1 = C.MATRIX_BASE_MM, C.MATRIX_BASE_MM + fr.wall_h
    ring = fr.prism(fr.c + fr.T, z0, z1) - fr.prism(fr.c, z0 - 1, z1 + 1)
    rib_top, rib_bottom = _edge_ribs(fr)
    ring = ring + rib_top + rib_bottom
    for hole in _pin_holes(fr):
        ring = ring - hole
    big = fr.S * 2
    gap = 0.2  # saw cut between the halves
    upper = ring ^ box(-big, gap / 2, z0 - 1, big, big, z1 + 1)
    lower = ring ^ box(-big, -big, z0 - 1, big, -gap / 2, z1 + 1)
    return {"frame_upper": from_manifold(upper), "frame_lower": from_manifold(lower)}


def _bore_dir() -> np.ndarray:
    """Unit vector of the hanging hole: into the tile from the back (-z in casting
    coordinates) and upwards (+y)."""
    a = math.radians(C.HANG_HOLE_ANGLE_DEG)
    return np.array([0.0, math.sin(a), -math.cos(a)])


def _cyl_along(p0: np.ndarray, d: np.ndarray, length: float, r: float) -> Manifold:
    """Cylinder from p0 along the unit vector d (d without x component)."""
    phi = math.degrees(math.atan2(-d[1], d[2]))  # rotation about x that maps +z onto d
    return Manifold.cylinder(length, r, r, 48).rotate([phi, 0.0, 0.0]).translate(list(p0))


def build_backplate(p: TileParams) -> trimesh.Trimesh:
    """Back plate: rests on the frame, a centring ring drops into the frame opening. Pressed
    down, it levels the rim and two solid pads; guide bosses over the pads lead the punch into
    the slanted hanging holes. Also: ID window (punches) and a TOP arrow."""
    fr = ToolFrame.from_params(p)
    zb = C.MATRIX_BASE_MM + fr.wall_h  # wall top = tile back
    t = C.BACKPLATE_THICKNESS_MM
    plate = fr.prism(fr.c + 4.0, zb, zb + t)
    ring = fr.prism(0.0, zb - 3.0, zb + 0.1) - fr.prism(-3.0, zb - 4.0, zb + 0.2)
    plate = plate + ring
    d = _bore_dir()
    guide = 16.0
    r_hole = C.HANG_HOLE_DIAMETER_MM / 2 + C.FIT_CLEARANCE_MM
    for x, y in fr.hanging_points():
        entry = np.array([x, y, zb])  # where the hole enters the clay
        boss = _cyl_along(entry - d * (guide + t), d, guide + t, r_hole + 4.0)
        boss = boss ^ box(x - 30, y - 30, zb, x + 30, y + 30, zb + 60)  # nothing below the plate
        plate = plate + boss
        plate = plate - _cyl_along(entry - d * (guide + t + 2.0), d, guide + t + 4.0, r_hole)
    s = fr.s
    wx, wy = 70.0 * s, (C.ID_CHAR_HEIGHT_MM + 4.0) * s
    yc = -0.2 * fr.S
    plate = plate - box(-wx / 2, yc - wy / 2, zb - 5, wx / 2, yc + wy / 2, zb + t + 1)
    top_y = fr.S / 2
    arrow = CrossSection([[(-8, top_y - 22), (8, top_y - 22), (0, top_y - 10)]])
    plate = plate - Manifold.extrude(arrow, t + 7).translate([0, 0, zb - 5])
    return from_manifold(plate)


def build_hole_punch(p: TileParams) -> trimesh.Trimesh:
    """Punch for the slanted hanging holes: rod through the guide boss, the stop collar sets
    the depth (HANG_HOLE_DEPTH_MM, scaled for shrinkage)."""
    guide = 16.0 + C.BACKPLATE_THICKNESS_MM
    depth = C.HANG_HOLE_DEPTH_MM * p.tool_scale
    r = C.HANG_HOLE_DIAMETER_MM / 2
    rod_len = guide + depth
    rod = Manifold.cylinder(rod_len, r, r, 48)
    collar = Manifold.cylinder(6.0, 9.0, 9.0, 64).translate([0, 0, rod_len])
    grip = Manifold.cylinder(30.0, 7.0, 7.0, 48).translate([0, 0, rod_len + 6.0])
    return from_manifold(rod + collar + grip)


def hanging_channel_clearance_mm(p: TileParams, channels: str) -> float:
    """Smallest distance (fired mm) between a hanging pad and a side channel."""
    if channels == "none":
        return float("inf")
    if channels == "edge_half":
        fr = ToolFrame.from_params(p.with_updates({"shrink_pct": 0.0}))
        pad_r = C.HANG_PAD_DIAMETER_MM / 2
        r_ch = C.HALF_CHANNEL_DIAMETER_MM / 2
        h = p.tile_size_mm / 2
        return min(h - abs(x) - pad_r - r_ch for x, _ in fr.hanging_points())
    raise NotImplementedError("through channels are a v1 feature")


def lay_flat(mesh: trimesh.Trimesh, name: str) -> trimesh.Trimesh:
    """Print orientation: walls on their outer face, plate upside down, rest as modelled."""
    m = mesh.copy()
    rot = {
        "frame_top": trimesh.transformations.rotation_matrix(np.radians(-90), [1, 0, 0]),
        "frame_bottom": trimesh.transformations.rotation_matrix(np.radians(90), [1, 0, 0]),
        "frame_left": trimesh.transformations.rotation_matrix(np.radians(-90), [0, 1, 0]),
        "frame_right": trimesh.transformations.rotation_matrix(np.radians(90), [0, 1, 0]),
        "frame_upper": trimesh.transformations.rotation_matrix(np.radians(-90), [1, 0, 0]),
        "frame_lower": trimesh.transformations.rotation_matrix(np.radians(90), [1, 0, 0]),
        "hole_punch": trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]),
    }.get(name)
    if rot is not None:
        m.apply_transform(rot)
    lo, hi = m.bounds
    m.apply_translation([-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]])
    return m


# -- build volume ------------------------------------------------------------------------------
BED_SMALL = min(C.PRINTER_PROFILES["bambu_a1_mini"]["volume_mm"][:2])  # 180 mm: most printers
BED_LARGE = min(C.PRINTER_PROFILES["bambu_p1s"]["volume_mm"][:2])  # 256 mm


def bed_fit_estimate(p: TileParams) -> dict[str, dict]:
    """Fast estimate for the editor (exact check runs on export): largest footprint side."""
    fr = ToolFrame.from_params(p)
    w, h = fr.lat.bbox
    matrix = max(w, h) * fr.s + 2 * fr.F
    frame = (fr.S if fr.lat.shape == "square" else w * fr.s) + 2 * (fr.c + fr.T)
    plate = max(w, h) * fr.s + 2 * (fr.c + 4.0)
    return {"matrix": {"extent_mm": round(matrix, 1)}, "frame": {"extent_mm": round(frame, 1)},
            "backplate": {"extent_mm": round(plate, 1)}}


def bed_check(bed: dict[str, dict]) -> Check:
    """pass: fits a 180 mm bed (most printers) · warn: needs 256 mm · fail: larger."""
    if all("fits_180" in v for v in bed.values()):
        if all(v["fits_180"] for v in bed.values()):
            return Check("bed_fit", "pass", None, BED_SMALL, "All parts fit a 180 mm print bed.")
        if all(v["fits"] for v in bed.values()):
            big = [k for k, v in bed.items() if not v["fits_180"]]
            return Check("bed_fit", "warn", None, BED_LARGE,
                         "Needs a 256 mm print bed for: " + ", ".join(big))
        return Check("bed_fit", "fail", None, BED_LARGE, "Too large for a 256 mm print bed.")
    need = max(v["extent_mm"] for v in bed.values())
    # long frame walls can be printed diagonally; the estimate ignores that (conservative)
    status = "pass" if need <= BED_SMALL else "warn" if need <= BED_LARGE else "fail"
    return Check("bed_fit", status, round(need, 1), BED_SMALL if status == "pass" else BED_LARGE,
                 "Largest part vs. print bed (mm): 180 mm fits most printers.")


@dataclass
class ToolSet:
    parts: dict[str, trimesh.Trimesh]  # casting position (for assembly preview)
    bed_checks: dict[str, dict]


def build_toolset(result: TileResult, grid_mm: float = C.EXPORT_GRID_MM) -> ToolSet:
    p = result.params
    parts: dict[str, trimesh.Trimesh] = {"matrix": build_matrix(result, grid_mm)}
    parts.update(build_frame_walls(p))
    parts["backplate"] = build_backplate(p)
    parts["hole_punch"] = build_hole_punch(p)
    small = C.PRINTER_PROFILES["bambu_a1_mini"]["volume_mm"]
    large = C.PRINTER_PROFILES["bambu_p1s"]["volume_mm"]
    bed = {}
    for name, m in parts.items():
        flat = lay_flat(m, name)  # check the actual print orientation
        fits_small, deg = footprint_fits(flat, small)
        fits_large, deg_l = (True, deg) if fits_small else footprint_fits(flat, large)
        bed[name] = {"fits": bool(fits_large), "fits_180": bool(fits_small),
                     "rotation_deg": deg if fits_small else (deg_l if fits_large else None),
                     "extent_mm": [round(float(v), 2) for v in m.extents],
                     "watertight": bool(m.is_watertight), "triangles": int(len(m.faces))}
    return ToolSet(parts=parts, bed_checks=bed)
