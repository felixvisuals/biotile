"""Placeholder images for the surface overview (replace with real photos later).

Renders 13 procedural surfaces (soft hillshade, monochrome) to apps/web/public/images/surfaces.
Run:  uv run python scripts/make_placeholder_surfaces.py
"""

from pathlib import Path

import numpy as np
from biotile_geometry.pdfs import _hillshade
from PIL import Image
from scipy import ndimage

OUT = Path(__file__).resolve().parents[1] / "apps" / "web" / "public" / "images" / "surfaces"
W, H = 600, 800


def noise(rng, sigma, aniso=(1, 1)):
    z = ndimage.gaussian_filter(rng.standard_normal((H, W)), (sigma * aniso[0], sigma * aniso[1]))
    return (z - z.mean()) / (z.std() + 1e-9)


def cells(rng, n):
    pts = rng.random((n, 2)) * [W, H]
    yy, xx = np.mgrid[0:H, 0:W]
    d1 = np.full((H, W), np.inf)
    d2 = np.full((H, W), np.inf)
    for px, py in pts:
        d = np.hypot(xx - px, yy - py)
        d2 = np.minimum(d2, np.maximum(d1, d))
        d1 = np.minimum(d1, d)
    return d2 - d1


def surfaces(rng):
    yield noise(rng, 3, (6, 0.4)) + 0.3 * noise(rng, 1.2)  # bark
    yield -np.sqrt(cells(rng, 40)) + 0.15 * noise(rng, 1.5)  # tafoni
    yield np.minimum(cells(rng, 70), 8) + 0.4 * noise(rng, 2)  # dry crack
    xx = np.arange(W)[None, :] * np.ones((H, 1))
    yield -np.abs(np.sin(xx / 22.0 + 0.8 * noise(rng, 40))) + 0.2 * noise(rng, 2)  # karren
    yield noise(rng, 1.5) + 0.6 * noise(rng, 8)  # sandstone
    yield -1.0 * (noise(rng, 2.5) > 1.0) + 0.5 * noise(rng, 6)  # lava pores
    yield noise(rng, 2, (0.3, 8)) + 0.4 * noise(rng, 10)  # slate
    yield np.floor(noise(rng, 25) * 3) + 0.3 * noise(rng, 2)  # plane bark plates
    yield noise(rng, 2, (10, 0.3))  # vine fibres
    yield -np.sqrt(cells(rng, 120)) + 0.4 * noise(rng, 3)  # moss cushions
    yield np.minimum(cells(rng, 25), 3) + 0.3 * noise(rng, 1)  # asphalt cracks
    yield noise(rng, 6) + 0.5 * noise(rng, 1.2)  # travertine
    yield -np.sqrt(cells(rng, 18)) + 0.3 * noise(rng, 4)  # big hollows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(2026)
    for i, z in enumerate(surfaces(rng), start=1):
        z = (z - z.min()) / (np.ptp(z) + 1e-9) * 40.0
        s = _hillshade(z, 1.0)
        img = (0.18 + 0.78 * s) * 0.92 + 0.08 * (z / 40.0)
        rgb = np.stack([img * 0.96, img * 0.96, img * 0.92], -1)
        Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8)).save(
            OUT / f"surface-{i:02d}.jpg", quality=82)
    print(f"wrote {i} images to {OUT}")


if __name__ == "__main__":
    main()
