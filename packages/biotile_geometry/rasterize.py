"""Mesh (e.g. Tripo GLB) -> aligned, orthographic max-Z height raster."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import trimesh
from scipy import ndimage
from scipy.spatial import ConvexHull

from . import heightfield as hf


@dataclass
class RawRaster:
    """Height raster of the generated sample in its own (unitless, normalised) scale.

    z: square raster, row 0 = +y edge. extent: side length in mesh units.
    """

    z: np.ndarray
    extent: float
    flipped: bool
    n_faces: int


def load_mesh(path_or_file, file_type: str | None = None) -> trimesh.Trimesh:
    loaded = trimesh.load(path_or_file, file_type=file_type, force="scene", process=False)
    if isinstance(loaded, trimesh.Scene):
        meshes = [g for g in loaded.dump(concatenate=False) if isinstance(g, trimesh.Trimesh)]
        if not meshes:
            raise ValueError("GLB contains no triangle mesh")
        mesh = trimesh.util.concatenate(meshes)
    else:
        mesh = loaded
    if len(mesh.faces) == 0:
        raise ValueError("mesh has no faces")
    return mesh


def align_to_dominant_plane(mesh: trimesh.Trimesh) -> np.ndarray:
    """4x4 transform: area-weighted PCA, least-variance axis -> +Z, centred at origin."""
    centers = mesh.triangles_center
    w = mesh.area_faces
    w = w / w.sum()
    mu = (centers * w[:, None]).sum(axis=0)
    d = centers - mu
    cov = (d * w[:, None]).T @ d
    evals, evecs = np.linalg.eigh(cov)  # ascending
    normal = evecs[:, 0]
    major = evecs[:, 2]
    # Deterministic sign convention.
    if normal[np.argmax(np.abs(normal))] < 0:
        normal = -normal
    if major[np.argmax(np.abs(major))] < 0:
        major = -major
    minor = np.cross(normal, major)
    rot = np.eye(4)
    rot[:3, :3] = np.stack([major, minor, normal])
    trans = np.eye(4)
    trans[:3, 3] = -mu
    return rot @ trans


def _sample_points(tris: np.ndarray, count: int, rng: np.random.Generator) -> np.ndarray:
    a = tris[:, 0]
    ab = tris[:, 1] - a
    ac = tris[:, 2] - a
    area = 0.5 * np.linalg.norm(np.cross(ab, ac), axis=1)
    p = area / area.sum()
    idx = rng.choice(len(tris), size=count, p=p)
    u = rng.random(count)
    v = rng.random(count)
    flip = u + v > 1.0
    u[flip], v[flip] = 1.0 - u[flip], 1.0 - v[flip]
    return a[idx] + ab[idx] * u[:, None] + ac[idx] * v[:, None]


def max_z_raster(vertices: np.ndarray, faces: np.ndarray, half: float, n: int, seed: int,
                 samples_per_px: float = 6.0) -> np.ndarray:
    """Orthographic top view: per cell the maximum Z (stamps cannot have undercuts anyway).

    Uses dense, seeded surface sampling plus every vertex; empty cells get the nearest value.
    """
    tris = vertices[faces]
    # Only faces visible from above take part (a z-buffer would hide the others anyway);
    # otherwise sparse samples on the top let the back face shine through.
    nz = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])[:, 2]
    tris = tris[nz > 0]
    lo = tris[:, :, :2].min(axis=1)
    hi = tris[:, :, :2].max(axis=1)
    keep = np.all(hi >= -half, axis=1) & np.all(lo <= half, axis=1)
    tris = tris[keep]
    if len(tris) == 0:
        raise ValueError("no geometry inside raster window")
    px = 2.0 * half / n
    z = np.full((n, n), -np.inf)
    rng = np.random.default_rng(seed)
    total = int(n * n * samples_per_px)
    chunk = 2_000_000

    def splat(pts: np.ndarray) -> None:
        col = np.floor((pts[:, 0] + half) / px).astype(np.int64)
        row = np.floor((half - pts[:, 1]) / px).astype(np.int64)
        ok = (col >= 0) & (col < n) & (row >= 0) & (row < n)
        np.maximum.at(z, (row[ok], col[ok]), pts[ok, 2])

    splat(tris.reshape(-1, 3))
    done = 0
    while done < total:
        k = min(chunk, total - done)
        splat(_sample_points(tris, k, rng))
        done += k
    empty = ~np.isfinite(z)
    if empty.all():
        raise ValueError("raster is empty")
    if empty.any():
        idx = ndimage.distance_transform_edt(empty, return_distances=False, return_indices=True)
        z = z[tuple(idx)]
    return z


def _inscribed_half_side(xy: np.ndarray) -> float:
    hull = ConvexHull(xy)
    eq = hull.equations  # a*x + b*y + c <= 0 inside
    corners = np.array([[1, 1], [1, -1], [-1, 1], [-1, -1]], dtype=float)
    lo, hi = 0.0, float(np.abs(xy).max())
    for _ in range(50):
        mid = 0.5 * (lo + hi)
        pts = corners * mid
        if np.all(pts @ eq[:, :2].T + eq[:, 2] <= 0):
            lo = mid
        else:
            hi = mid
    if lo <= 0:
        raise ValueError("sample footprint does not contain its centroid")
    return lo


def rasterize_mesh(mesh: trimesh.Trimesh, n_out: int, seed: int,
                   crop_fraction: float = 0.7) -> RawRaster:
    """Align the sample, raster its relief side, and return a raster that is large enough
    to be rotated by any angle and then centre-cropped to `crop_fraction` of the extent.
    """
    t = align_to_dominant_plane(mesh)
    v = trimesh.transform_points(mesh.vertices, t)
    # Largest centred axis-aligned square inside the footprint (the in-plane PCA axes of a
    # square sample are arbitrary, so min(ptp) would overshoot the sample's corners).
    ext = 2.0 * _inscribed_half_side(v[:, :2])
    raster_fraction = min(0.99, crop_fraction * np.sqrt(2.0))
    half = 0.5 * raster_fraction * ext
    n_raw = int(np.ceil(n_out * raster_fraction / crop_fraction))
    faces = np.asarray(mesh.faces)

    # Decide which side carries the relief: the one with the larger detrended roughness.
    probe_n = 256
    top = max_z_raster(v, faces, half, probe_n, seed, samples_per_px=2.0)
    vb = v * np.array([1.0, -1.0, -1.0])  # rotate 180 deg about x (keeps handedness)
    bottom = max_z_raster(vb, faces, half, probe_n, seed, samples_per_px=2.0)
    flipped = float(np.std(hf.detrend(bottom))) > float(np.std(hf.detrend(top)))
    verts = vb if flipped else v
    z = max_z_raster(verts, faces, half, n_raw, seed)
    return RawRaster(z=z, extent=2.0 * half, flipped=flipped, n_faces=int(len(faces)))
