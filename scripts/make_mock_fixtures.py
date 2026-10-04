"""Generate synthetic Tripo-like GLB fixtures for MockTripoClient.

These stand in for real Tripo image-to-model results until live responses are recorded
(TRIPO_MODE=live TRIPO_RECORD=1). Each fixture is a slab of ~1 unit side with a seeded
procedural relief on one face, deliberately tilted so the alignment step is exercised.

Run:  uv run python scripts/make_mock_fixtures.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import trimesh
from biotile_geometry.mesh import heightfield_solid
from scipy import ndimage

OUT = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "tripo"
N = 360


def _noise(rng: np.random.Generator, n: int, sigma: float) -> np.ndarray:
    z = ndimage.gaussian_filter(rng.standard_normal((n, n)), sigma, mode="wrap")
    return (z - z.mean()) / (z.std() + 1e-12)


def tafoni(rng: np.random.Generator, n: int) -> np.ndarray:
    """Honeycomb weathering: distance to random cell centres -> rounded cavities."""
    pts = rng.random((60, 2))
    yy, xx = np.mgrid[0:n, 0:n] / n
    d = np.full((n, n), np.inf)
    d2 = np.full((n, n), np.inf)
    for px, py in pts:
        dd = np.hypot(xx - px, yy - py)
        d2 = np.minimum(d2, np.maximum(d, dd))
        d = np.minimum(d, dd)
    z = -np.sqrt(d2 - d + 1e-4)  # cavities in the cells, crisp ridges on the cell borders
    z = ndimage.gaussian_filter(z, 1.2, mode="wrap")  # sub-grid ridges would alias into teeth
    z = (z - z.min()) / np.ptp(z) * 0.08 + _noise(rng, n, 2.0) * 0.004
    return z


def bark(rng: np.random.Generator, n: int) -> np.ndarray:
    """Vertical furrows of varying depth with plates in between."""
    x = np.linspace(0, 1, n)
    furrows = np.zeros(n)
    for c in rng.random(14):
        w = rng.uniform(0.006, 0.02)
        furrows -= rng.uniform(0.3, 1.0) * np.exp(-((x - c) / w) ** 2)
    z = np.tile(furrows, (n, 1))
    z += ndimage.gaussian_filter1d(rng.standard_normal((n, n)), 12, axis=0) * 0.15
    z = z * 0.07 + _noise(rng, n, 1.5) * 0.004
    return z


def karren(rng: np.random.Generator, n: int) -> np.ndarray:
    """Solution flutes: parallel rounded channels running down the slope."""
    x = np.linspace(0, 1, n)
    y = np.linspace(0, 1, n)[:, None]
    wobble = 0.03 * np.sin(2 * np.pi * (y * 1.3 + rng.random()))
    z = -np.abs(np.sin(np.pi * 7 * (x[None, :] + wobble))) ** 0.6
    z = z * 0.06 + _noise(rng, n, 6) * 0.01 + _noise(rng, n, 1.2) * 0.003
    return z


GENERATORS = {"tafoni": tafoni, "bark": bark, "karren": karren}


def make(name: str, seed: int) -> trimesh.Trimesh:
    rng = np.random.default_rng(seed)
    relief = GENERATORS[name](rng, N)
    dx = 1.0 / (N - 1)
    top = 0.2 + relief - relief.min() + 0.01
    mesh = heightfield_solid(top, -0.5, -0.5, dx, z_bottom=0.0)
    # Tilt and spin like an arbitrarily oriented generated object.
    t = trimesh.transformations.euler_matrix(0.35, -0.2, 0.9)
    mesh.apply_transform(t)
    return mesh


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    index = {}
    for i, name in enumerate(GENERATORS):
        mesh = make(name, 1000 + i)
        glb = OUT / f"synthetic_{name}.glb"
        mesh.export(glb)
        index[name] = {"model": glb.name, "synthetic": True}
        print(f"{glb.name}: {len(mesh.faces)} faces, {glb.stat().st_size / 1e6:.1f} MB")
    (OUT / "synthetic_index.json").write_text(json.dumps(index, indent=2) + "\n")


if __name__ == "__main__":
    main()
