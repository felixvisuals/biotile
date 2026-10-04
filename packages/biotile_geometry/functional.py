"""Functional layer for the moss starter (brief 5.5.1), for square and hexagonal tiles.

Templates
  moss_nests        (default) organically placed pockets ("nests"), preferably in the natural
                    hollows of the photographed surface, fed by fine rills that follow the
                    valleys of the texture down into the nests.
  diagonal_cascade  continuous diagonal channels with anchor holes (Jakubovskis 2025: continuous
                    diagonal booster shapes distributed water best).
  none              texture only.

Everything is computed on the lattice torus (see lattice.py), so it tiles seamlessly.
Nests and channels have a guaranteed depth below the reference plane; rills are cut
relative to the surface (they run inside valleys, an absolute depth would vanish there).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy import ndimage
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra

from . import constants as C
from .lattice import Lattice, periodic_edt

TEMPLATES = ("moss_nests", "diagonal_cascade", "none")


@dataclass(frozen=True)
class FunctionalParams:
    template: str = "moss_nests"
    # moss nests
    nest_spacing_mm: float = C.NEST_SPACING_DEFAULT_MM
    nest_size_mm: float = C.NEST_WIDTH_DEFAULT_MM
    nest_depth_mm: float = C.NEST_DEPTH_DEFAULT_MM
    rills: bool = True
    # diagonal channels
    channel_depth_mm: float = C.BOOSTER_CHANNEL_DEPTH_DEFAULT_MM
    channel_width_mm: float = C.BOOSTER_CHANNEL_WIDTH_DEFAULT_MM
    channel_count: int = 2
    anchor_holes: bool = True
    direction: str = "down_right"  # down_right | down_left
    seed: int = 7

    def validate(self) -> list[str]:
        errs = []
        if self.template not in TEMPLATES:
            errs.append(f"unknown functional template {self.template!r}")
        lo, hi = C.BOOSTER_CHANNEL_DEPTH_RANGE_MM
        if not lo <= self.channel_depth_mm <= hi:
            errs.append(f"channel depth must be within {lo}-{hi} mm")
        lo, hi = C.BOOSTER_CHANNEL_WIDTH_RANGE_MM
        if not lo <= self.channel_width_mm <= hi:
            errs.append(f"channel width must be within {lo}-{hi} mm")
        if self.channel_count not in (2, 3, 4):
            errs.append("channel_count must be 2, 3 or 4 (channels must divide the tile, "
                        "otherwise the pattern does not tile)")
        lo, hi = C.NEST_WIDTH_RANGE_MM
        if not lo <= self.nest_size_mm <= hi:
            errs.append(f"nest size must be within {lo}-{hi} mm")
        lo, hi = C.NEST_SPACING_RANGE_MM
        if not lo <= self.nest_spacing_mm <= hi:
            errs.append(f"nest spacing must be within {lo}-{hi} mm")
        lo, hi = C.NEST_DEPTH_RANGE_MM
        if not lo <= self.nest_depth_mm <= hi:
            errs.append(f"nest depth must be within {lo}-{hi} mm")
        if self.direction not in ("down_right", "down_left"):
            errs.append("direction must be down_right or down_left")
        return errs


def build_functional(lat: Lattice, n: int, p: FunctionalParams, texture: np.ndarray,
                     macro: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (absolute carve <= 0, relative carve <= 0, anchor mask) on the index grid."""
    zero = np.zeros((n, n))
    if p.template == "none":
        return zero, zero, np.zeros((n, n), dtype=bool)
    if p.template == "diagonal_cascade":
        carve, anchor = diagonal_channels(lat, n, p)
        return carve, zero, anchor
    if p.template == "moss_nests":
        pts = place_nests(lat, n, p, macro)
        carve = nests_field(lat, n, p, pts)
        rel = rills_field(lat, n, p, pts, texture) if p.rills else zero
        return carve, rel, np.zeros((n, n), dtype=bool)
    raise ValueError(f"template {p.template!r} not implemented")


# -- diagonal channels -----------------------------------------------------------------
def _channel_lattice_vector(lat: Lattice, direction: str) -> tuple[int, int]:
    """Integer (a, b) with w = a e_s + b e_t: channels run along w (a lattice vector)."""
    if lat.shape == "square":  # e_t points down: e_s + e_t descends to the right
        return (1, 1) if direction == "down_right" else (1, -1)
    return (1, -1) if direction == "down_right" else (1, 0)


def diagonal_channels(lat: Lattice, n: int, p: FunctionalParams) -> tuple[np.ndarray, np.ndarray]:
    a, b = _channel_lattice_vector(lat, p.direction)
    w = lat.basis @ np.array([a, b], dtype=float)
    w_len = float(np.hypot(*w))
    c = (np.arange(n) + 0.5) / n
    s, t = np.meshgrid(c, c)
    k = p.channel_count
    u = b * s - a * t  # constant along w, periodic mod 1
    spacing_perp = lat.cell_area / w_len / k
    dist = (((u * k) % 1.0) - 0.5) * spacing_perp
    half = p.channel_width_mm / 2.0
    floor_half = p.channel_width_mm / 4.0
    q = np.clip((np.abs(dist) - floor_half) / (half - floor_half), 0.0, 1.0)
    carve = -p.channel_depth_mm * 0.5 * (1.0 + np.cos(np.pi * q)) * (np.abs(dist) < half)
    anchor = np.zeros((n, n), dtype=bool)
    if p.anchor_holes:
        # Position along the channel: projection onto w. Every lattice vector projects onto
        # a multiple of |w| / 2 (square and hex), so an even hole count m keeps it periodic.
        m = max(2, 2 * round(w_len / C.ANCHOR_HOLE_PITCH_MM / 2))
        x, y = lat.grid_points(n)
        proj = (x * w[0] + y * w[1]) / w_len
        pitch = w_len / m
        along = ((proj / pitch) % 1.0 - 0.5) * pitch
        r = C.ANCHOR_HOLE_DIAMETER_MM / 2.0
        anchor = (dist**2 + along**2) <= r * r
    return carve, anchor


# -- moss nests --------------------------------------------------------------------------
def place_nests(lat: Lattice, n: int, p: FunctionalParams, macro: np.ndarray) -> np.ndarray:
    """Nest centres (mm): first in the deepest natural hollows of the macro relief, then
    blue-noise fill, always keeping the minimum spacing on the torus."""
    x, y = lat.grid_points(n)
    pts: list[tuple[float, float]] = []

    def far_enough(px: float, py: float) -> bool:
        if not pts:
            return True
        arr = np.array(pts)
        dx, dy = lat.min_image(arr[:, 0] - px, arr[:, 1] - py)
        return bool(np.all(np.hypot(dx, dy) >= p.nest_spacing_mm))

    # 1) natural hollows: local minima of the macro band, deepest first
    win = max(3, int(round(p.nest_spacing_mm / 2 / lat.px_mm(n))) | 1)
    minima = (macro == ndimage.minimum_filter(macro, size=win, mode="wrap"))
    ii, jj = np.nonzero(minima)
    order = np.argsort(macro[ii, jj])
    deep_limit = np.percentile(macro, 35)
    for k in order:
        if macro[ii[k], jj[k]] > deep_limit:
            break
        if far_enough(x[ii[k], jj[k]], y[ii[k], jj[k]]):
            pts.append((float(x[ii[k], jj[k]]), float(y[ii[k], jj[k]])))
    # 2) blue-noise fill of the remaining area
    rng = np.random.default_rng(p.seed)
    for _ in range(4000):
        s, t = rng.random(2)
        q = lat.origin + lat.basis @ np.array([s, t])
        if far_enough(q[0], q[1]):
            pts.append((float(q[0]), float(q[1])))
    return np.array(pts) if pts else np.zeros((0, 2))


def nests_field(lat: Lattice, n: int, p: FunctionalParams, pts: np.ndarray) -> np.ndarray:
    """Asymmetric pockets: steep lower flank (a shelf that holds the moss when the tile
    hangs), gentle upper flank where water runs in. A height field: no undercuts."""
    x, y = lat.grid_points(n)
    out = np.zeros((n, n))
    rx = p.nest_size_mm / 2.0
    up = p.nest_size_mm * C.NEST_UP_FACTOR
    down = p.nest_size_mm * C.NEST_DOWN_FACTOR
    for px, py in pts:
        dx, dy = lat.min_image(x - px, y - py)
        ry = np.where(dy > 0, up, down)
        q2 = (dx / rx) ** 2 + (dy / ry) ** 2
        out = np.minimum(out, -p.nest_depth_mm * np.clip(1.0 - q2, 0.0, 1.0) ** 0.6)
    return out


def rills_field(lat: Lattice, n: int, p: FunctionalParams, pts: np.ndarray,
                texture: np.ndarray, grid: int = 240) -> np.ndarray:
    """Fine rills (relative depth) along least-cost paths: cheap in texture valleys,
    expensive uphill, from every nest down to the nearest nest below (on the torus)."""
    if len(pts) < 2:
        return np.zeros((n, n))
    g = grid
    t = ndimage.zoom(texture, g / n, order=1, mode="grid-wrap", grid_mode=True)
    t = (t - t.min()) / (np.ptp(t) + 1e-9)
    idx = np.arange(g * g).reshape(g, g)
    rows, cols, wts = [], [], []
    for di, dj, vec in lat.step_vectors(g):
        nb = np.roll(np.roll(idx, -di, 0), -dj, 1)
        tn = np.roll(np.roll(t, -di, 0), -dj, 1)
        length = float(np.hypot(*vec)) / lat.px_mm(g)
        uphill = 6.0 if vec[1] > 1e-9 else 0.0
        cost = length * (0.1 + 3.0 * (t * t + tn * tn)) + uphill
        rows.append(idx.ravel())
        cols.append(nb.ravel())
        wts.append(cost.ravel())
    graph = coo_matrix((np.concatenate(wts), (np.concatenate(rows), np.concatenate(cols))),
                       shape=(g * g, g * g)).tocsr()
    inv = np.linalg.inv(lat.basis)

    def cell(pt: np.ndarray) -> int:
        st = inv @ (pt - lat.origin)
        j = int(np.floor((st[0] % 1.0) * g)) % g
        i = int(np.floor((st[1] % 1.0) * g)) % g
        return int(idx[i, j])

    scale = lat.size / C.TILE_SIZE_MM
    mask = np.zeros((n, n), dtype=bool)
    for a in range(len(pts)):
        dx, dy = lat.min_image(pts[:, 0] - pts[a, 0], pts[:, 1] - pts[a, 1])
        ok = (dy <= -15 * scale) & (dy >= -90 * scale)
        ok[a] = False
        if not ok.any():
            continue
        score = np.where(ok, np.abs(dx) + 0.3 * np.abs(dy), np.inf)
        b = int(np.argmin(score))
        src, dst = cell(pts[a]), cell(pts[b])
        _, pred = dijkstra(graph, indices=src, return_predecessors=True)
        path, k = [], dst
        while k != src and k >= 0:
            path.append((k // g, k % g))
            k = pred[k]
        path.append((src // g, src % g))
        if len(path) < 3:
            continue
        cells = np.array(path[::-1], dtype=float)
        steps = (np.diff(cells, axis=0) + g / 2) % g - g / 2
        line = np.vstack([cells[:1], cells[0] + np.cumsum(steps, axis=0)])
        line = ndimage.gaussian_filter1d(line, sigma=5.0, axis=0, mode="nearest")
        # draw the smoothed path on the full-resolution grid (no blocky rill edges)
        line = (line + 0.5) * (n / g) - 0.5
        dense = np.vstack([np.linspace(line[i], line[i + 1], 12, endpoint=False)
                           for i in range(len(line) - 1)] + [line[-1:]])
        mask[np.round(dense[:, 0]).astype(int) % n, np.round(dense[:, 1]).astype(int) % n] = True
    dist_mm = periodic_edt(mask) * lat.px_mm(n)
    half = C.RILL_WIDTH_MM / 2.0
    return -C.RILL_DEPTH_MM * 0.5 * (1.0 + np.cos(np.pi * np.clip(dist_mm / half, 0.0, 1.0)))


def flow_path_length_mm(lat: Lattice, p: FunctionalParams) -> float:
    """Total channel length per tile (k parallel lines, each one lattice vector long)."""
    if p.template == "diagonal_cascade":
        a, b = _channel_lattice_vector(lat, p.direction)
        return p.channel_count * float(np.hypot(*(lat.basis @ np.array([a, b], dtype=float))))
    return 0.0


def nest_count(lat: Lattice, p: FunctionalParams) -> int:
    """Rough number of nests per tile (for labels)."""
    return max(1, int(round(lat.cell_area / (math.pi * (p.nest_spacing_mm / 2) ** 2) * 0.7)))
