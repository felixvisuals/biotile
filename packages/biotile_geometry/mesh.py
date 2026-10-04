"""Watertight solids from height fields, boolean helpers and export decimation."""

from __future__ import annotations

import numpy as np
import trimesh
from manifold3d import CrossSection, Manifold, Mesh
from scipy.spatial import ConvexHull

from . import constants as C


def heightfield_solid(top: np.ndarray, x0: float, y0: float, dx: float, z_bottom: float = 0.0
                      ) -> trimesh.Trimesh:
    """Closed solid between z_bottom and the node height grid `top`.

    top[i, j] is the height at x = x0 + j*dx, y = y0 + (ny-1-i)*dx (row 0 = max y).
    """
    ny, nx = top.shape
    if np.any(top <= z_bottom):
        raise ValueError("height field must lie strictly above z_bottom")
    jj, ii = np.meshgrid(np.arange(nx), np.arange(ny))
    xs = x0 + jj * dx
    ys = y0 + (ny - 1 - ii) * dx
    v_top = np.column_stack([xs.ravel(), ys.ravel(), top.ravel()])
    idx = np.arange(ny * nx).reshape(ny, nx)
    a = idx[:-1, :-1].ravel()
    b = idx[:-1, 1:].ravel()
    c = idx[1:, :-1].ravel()
    d = idx[1:, 1:].ravel()
    f_top = np.concatenate([np.column_stack([c, d, b]), np.column_stack([c, b, a])])

    ring = np.concatenate([
        idx[ny - 1, :],  # bottom row, left -> right
        idx[ny - 2::-1, nx - 1],  # right column, bottom -> top
        idx[0, nx - 2::-1],  # top row, right -> left
        idx[1:ny - 1, 0],  # left column, top -> bottom (excluding corners)
    ])
    m = len(ring)
    base = ny * nx
    v_bot = v_top[ring].copy()
    v_bot[:, 2] = z_bottom
    center = np.array([[x0 + (nx - 1) * dx / 2, y0 + (ny - 1) * dx / 2, z_bottom]])
    k = np.arange(m)
    k1 = (k + 1) % m
    tk, tk1 = ring[k], ring[k1]
    bk, bk1 = base + k, base + k1
    f_side = np.concatenate([np.column_stack([bk, bk1, tk1]), np.column_stack([bk, tk1, tk])])
    cidx = base + m
    f_bot = np.column_stack([np.full(m, cidx), bk1, bk])
    verts = np.vstack([v_top, v_bot, center])
    faces = np.vstack([f_top, f_side, f_bot])
    return trimesh.Trimesh(verts, faces, process=False)


def decimate(mesh: trimesh.Trimesh, max_faces: int = C.EXPORT_MAX_TRIANGLES) -> trimesh.Trimesh:
    """Quadric decimation; returns the input unchanged if it is already small enough or if
    decimation would break watertightness."""
    if len(mesh.faces) <= max_faces:
        return mesh
    import fast_simplification

    reduction = 1.0 - max_faces / len(mesh.faces)
    pts, fcs = fast_simplification.simplify(
        np.asarray(mesh.vertices, dtype=np.float32), np.asarray(mesh.faces, dtype=np.int32),
        target_reduction=reduction)
    out = trimesh.Trimesh(pts, fcs, process=True)
    if not out.is_watertight:
        return mesh
    return out


def to_manifold(mesh: trimesh.Trimesh) -> Manifold:
    m = Manifold(Mesh(vert_properties=np.asarray(mesh.vertices, dtype=np.float32),
                      tri_verts=np.asarray(mesh.faces, dtype=np.uint32)))
    if m.status().name != "NoError":
        raise ValueError(f"mesh is not a valid manifold: {m.status()}")
    return m


def from_manifold(m: Manifold) -> trimesh.Trimesh:
    mm = m.to_mesh()
    return trimesh.Trimesh(np.asarray(mm.vert_properties)[:, :3], np.asarray(mm.tri_verts),
                           process=True)


def box(x0: float, y0: float, z0: float, x1: float, y1: float, z1: float) -> Manifold:
    return Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])


def cylinder_z(cx: float, cy: float, z0: float, z1: float, r: float, segments: int = 48
               ) -> Manifold:
    return Manifold.cylinder(z1 - z0, r, r, segments).translate([cx, cy, z0])


def extrude_polygon(points: list[tuple[float, float]], z0: float, z1: float) -> Manifold:
    return Manifold.extrude(CrossSection([points]), z1 - z0).translate([0.0, 0.0, z0])


def union_all(parts: list[Manifold]) -> Manifold:
    return Manifold.batch_boolean(parts, _op("Add")) if len(parts) > 1 else parts[0]


def _op(name: str):
    from manifold3d import OpType

    return getattr(OpType, name)


def footprint_fits(mesh: trimesh.Trimesh, volume_mm: tuple[float, float, float],
                   flat_only: bool = True) -> tuple[bool, float]:
    """Check whether the part fits the build volume in its print orientation, allowing any
    rotation about Z (e.g. long frame walls printed diagonally). With flat_only=False the
    other two flat orientations are tried as well.

    Returns (fits, best_rotation_deg).
    """
    bx, by, bz = volume_mm
    verts = np.asarray(mesh.vertices)
    for axes in ((0, 1, 2),) if flat_only else ((0, 1, 2), (0, 2, 1), (1, 2, 0)):
        pts = verts[:, axes]
        h = np.ptp(pts[:, 2])
        if h > bz:
            continue
        xy = pts[:, :2]
        if len(xy) > 3:
            xy = xy[ConvexHull(xy).vertices]
        for deg in np.arange(0.0, 90.0, 0.5):
            t = np.radians(deg)
            r = np.array([[np.cos(t), -np.sin(t)], [np.sin(t), np.cos(t)]])
            q = xy @ r.T
            w, d = np.ptp(q[:, 0]), np.ptp(q[:, 1])
            if (w <= bx and d <= by) or (w <= by and d <= bx):
                return True, float(deg)
    return False, float("nan")
