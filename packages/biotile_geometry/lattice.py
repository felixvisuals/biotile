"""Tiling lattices: square tiles and hexagonal ("Barcelona") tiles.

A periodic pattern is stored on an n x n index grid over one period cell of the lattice:
    point(i, j) = origin + s * e_s + t * e_t,   s = (j + 0.5) / n,  t = (i + 0.5) / n
Wrapping the index grid in both directions is exactly periodicity under the lattice, so any
field computed with wrap-around index operations tiles seamlessly, for squares and hexagons.

Square tile (side S):   e_s = (S, 0), e_t = (0, -S), origin (0, S)  -> row 0 = top edge,
                        which is the convention used everywhere else in the package.
Hexagonal tile (flat-top, flat-to-flat = S, side a = S / sqrt 3):
                        e_s = (1.5 a, S / 2), e_t = (0, S), origin chosen so the hexagon
                        centre is the origin. All six neighbour steps of the skew grid have the
                        same length S / n, so the index grid is a true hexagonal grid.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy import ndimage


@dataclass(frozen=True)
class Lattice:
    shape: str  # "square" | "hex"
    size: float  # square: side; hex: flat-to-flat distance (mm)

    # -- geometry of one tile ---------------------------------------------------------
    @property
    def side(self) -> float:
        return self.size if self.shape == "square" else self.size / math.sqrt(3.0)

    @property
    def basis(self) -> np.ndarray:
        """Columns e_s, e_t (mm)."""
        if self.shape == "square":
            return np.array([[self.size, 0.0], [0.0, -self.size]])
        a = self.side
        return np.array([[1.5 * a, 0.0], [self.size / 2.0, self.size]])

    @property
    def origin(self) -> np.ndarray:
        return np.array([0.0, self.size]) if self.shape == "square" else np.zeros(2)

    @property
    def bbox(self) -> tuple[float, float]:
        """Width, height of one tile (mm)."""
        return (self.size, self.size) if self.shape == "square" else (2.0 * self.side, self.size)

    @property
    def cell_area(self) -> float:
        return abs(float(np.linalg.det(self.basis)))

    def outline(self) -> list[tuple[float, float]]:
        """Tile outline, counter-clockwise, in tile coordinates (square: origin bottom-left,
        hex: origin at the centre)."""
        if self.shape == "square":
            s = self.size
            return [(0.0, 0.0), (s, 0.0), (s, s), (0.0, s)]
        a = self.side
        return [(a * math.cos(k * math.pi / 3), a * math.sin(k * math.pi / 3)) for k in range(6)]

    def tile_center(self) -> np.ndarray:
        return np.array([self.size / 2, self.size / 2]) if self.shape == "square" else np.zeros(2)

    # -- index grid -------------------------------------------------------------------
    def grid_points(self, n: int) -> tuple[np.ndarray, np.ndarray]:
        c = (np.arange(n) + 0.5) / n
        s, t = np.meshgrid(c, c)  # s varies along columns (j), t along rows (i)
        b = self.basis
        x = self.origin[0] + s * b[0, 0] + t * b[0, 1]
        y = self.origin[1] + s * b[1, 0] + t * b[1, 1]
        return x, y

    def step_vectors(self, n: int) -> list[tuple[int, int, np.ndarray]]:
        """Neighbour index steps (di, dj) with their cartesian vector (mm)."""
        b = self.basis / n
        if self.shape == "square":
            steps = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]
        else:  # hexagonal neighbourhood of the skew grid (all equal length)
            steps = [(-1, 0), (1, 0), (0, -1), (0, 1), (1, -1), (-1, 1)]
        return [(di, dj, b @ np.array([dj, di], dtype=float)) for di, dj in steps]

    def px_mm(self, n: int) -> float:
        return self.size / n

    # -- periodic geometry -------------------------------------------------------------
    def min_image(self, dx: np.ndarray, dy: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Shortest representative of difference vectors under the lattice."""
        inv = np.linalg.inv(self.basis)
        cs = inv[0, 0] * dx + inv[0, 1] * dy
        ct = inv[1, 0] * dx + inv[1, 1] * dy
        cs = cs - np.round(cs)
        ct = ct - np.round(ct)
        b = self.basis
        best_x = best_y = None
        best_d = None
        for oi in (-1, 0, 1):
            for oj in (-1, 0, 1):
                x = (cs + oi) * b[0, 0] + (ct + oj) * b[0, 1]
                y = (cs + oi) * b[1, 0] + (ct + oj) * b[1, 1]
                d = x * x + y * y
                if best_d is None:
                    best_x, best_y, best_d = x, y, d
                else:
                    m = d < best_d
                    best_x = np.where(m, x, best_x)
                    best_y = np.where(m, y, best_y)
                    best_d = np.where(m, d, best_d)
        return best_x, best_y

    def to_index(self, x: np.ndarray, y: np.ndarray, n: int) -> tuple[np.ndarray, np.ndarray]:
        """Fractional (row, col) index coordinates for map_coordinates with grid-wrap."""
        inv = np.linalg.inv(self.basis)
        dx = x - self.origin[0]
        dy = y - self.origin[1]
        s = inv[0, 0] * dx + inv[0, 1] * dy
        t = inv[1, 0] * dx + inv[1, 1] * dy
        return t * n - 0.5, s * n - 0.5

    def sample(self, field: np.ndarray, x: np.ndarray, y: np.ndarray, order: int = 1) -> np.ndarray:
        """Evaluate a periodic index-grid field at cartesian points (exactly periodic)."""
        n = field.shape[0]
        r, c = self.to_index(x, y, n)
        return ndimage.map_coordinates(field, [r % n, c % n], order=order, mode="grid-wrap")

    # -- tile raster (cartesian, for tools and previews) --------------------------------
    def tile_raster(self, n_y: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
        """Cartesian grid over the tile bbox (row 0 = top). Returns x, y, inside-mask, px."""
        w, h = self.bbox
        px = h / n_y
        n_x = int(round(w / px))
        cx = (np.arange(n_x) + 0.5) * px
        cy = h - (np.arange(n_y) + 0.5) * px
        x, y = np.meshgrid(cx, cy)
        if self.shape == "hex":
            x = x - w / 2
            y = y - h / 2
        inside = self.edge_distance(x, y) >= 0
        return x, y, inside, px

    def edge_distance(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        """Distance to the tile border (positive inside)."""
        if self.shape == "square":
            s = self.size
            return np.minimum(np.minimum(x, s - x), np.minimum(y, s - y))
        r_in = self.size / 2
        d = np.full(np.shape(x), np.inf)
        for ang in (90.0, 30.0, -30.0):
            nx, ny = math.cos(math.radians(ang)), math.sin(math.radians(ang))
            d = np.minimum(d, r_in - np.abs(nx * x + ny * y))
        return d


def periodic_edt(mask: np.ndarray) -> np.ndarray:
    """Distance (index units) to the nearest True cell, wrapping around the grid."""
    n = mask.shape[0]
    d = ndimage.distance_transform_edt(np.tile(~mask, (3, 3)))
    return d[n:2 * n, n:2 * n]
