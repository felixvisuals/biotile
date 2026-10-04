"""Height-field operations on square rasters (values in mm, z up, row 0 = top edge).

All operations are deterministic (no randomness) so equal input gives equal output.
"""

from __future__ import annotations

import math

import numpy as np
from scipy import ndimage

# ISO 16610-21 Gaussian filter: sigma = lambda_c * sqrt(ln 2 / pi) / sqrt(2 pi)
_ISO_GAUSS_SIGMA_PER_CUTOFF = math.sqrt(math.log(2.0) / math.pi) / math.sqrt(2.0 * math.pi)


def detrend(z: np.ndarray, order: int = 2) -> np.ndarray:
    """Subtract a least-squares 2D polynomial surface of the given total order."""
    n_rows, n_cols = z.shape
    v = np.linspace(-1.0, 1.0, n_rows)
    u = np.linspace(-1.0, 1.0, n_cols)
    uu, vv = np.meshgrid(u, v)
    terms = [uu**i * vv**j for i in range(order + 1) for j in range(order + 1 - i)]
    a = np.stack([t.ravel() for t in terms], axis=1)
    # Subsample rows for speed on large rasters; the fit is smooth anyway.
    step = max(1, (n_rows * n_cols) // 250_000)
    coeffs, *_ = np.linalg.lstsq(a[::step], z.ravel()[::step], rcond=None)
    return z - (a @ coeffs).reshape(z.shape)


def periodic_component(z: np.ndarray) -> np.ndarray:
    """Periodic part of the periodic-plus-smooth decomposition (Moisan 2011).

    The smooth part absorbs the boundary discontinuities, so the returned image tiles
    seamlessly while keeping all interior detail.
    """
    m, n = z.shape
    v = np.zeros_like(z, dtype=np.float64)
    v[0, :] += z[-1, :] - z[0, :]
    v[-1, :] += z[0, :] - z[-1, :]
    v[:, 0] += z[:, -1] - z[:, 0]
    v[:, -1] += z[:, 0] - z[:, -1]
    q = np.arange(m).reshape(m, 1)
    r = np.arange(n).reshape(1, n)
    denom = 2.0 * np.cos(2.0 * np.pi * q / m) + 2.0 * np.cos(2.0 * np.pi * r / n) - 4.0
    denom[0, 0] = 1.0
    s_hat = np.fft.fft2(v) / denom
    s_hat[0, 0] = 0.0
    smooth = np.real(np.fft.ifft2(s_hat))
    return z - smooth


def heal_seams(z: np.ndarray, band_fraction: float = 0.12) -> np.ndarray:
    """Make a periodic field smooth (not only continuous) across its seams.

    Near each border the field is cross-faded with a copy shifted by half a period, whose
    values there come from the image interior and are therefore smooth across the seam.
    The blend is variance-preserving (w z1 + (1-w) z2) / sqrt(w^2 + (1-w)^2), so the
    roughness does not fade in the band. Applied along x, then along y.
    """
    n = z.shape[0]
    b = max(2, int(round(n * band_fraction)))
    d = np.minimum(np.arange(n), n - 1 - np.arange(n)).astype(float)
    t = np.clip(d / b, 0.0, 1.0)
    w = t * t * (3 - 2 * t)  # 0 at the seam, 1 inside
    norm = np.sqrt(w**2 + (1 - w) ** 2)
    out = z.astype(np.float64)
    for axis in (1, 0):
        shifted = np.roll(out, n // 2, axis=axis)
        ww = w[None, :] if axis == 1 else w[:, None]
        nn = norm[None, :] if axis == 1 else norm[:, None]
        mean = out.mean()
        out = (ww * (out - mean) + (1 - ww) * (shifted - mean)) / nn + mean
    return out


def seam_curvature_ratio(z: np.ndarray) -> float:
    """Second difference across the seams vs. inside: ~1 = no visible crease."""
    seam = 0.5 * (np.mean(np.abs(z[1, :] - 2 * z[0, :] + z[-1, :]))
                  + np.mean(np.abs(z[:, 1] - 2 * z[:, 0] + z[:, -1])))
    inner = 0.5 * (np.mean(np.abs(np.diff(z, 2, axis=0))) + np.mean(np.abs(np.diff(z, 2, axis=1))))
    return float(seam / inner) if inner > 1e-12 else 1.0


def gaussian_lowpass(z: np.ndarray, cutoff_mm: float, px_mm: float, periodic: bool = True
                     ) -> np.ndarray:
    """ISO 16610-21 style Gaussian low-pass with the given cut-off wavelength."""
    sigma_px = cutoff_mm * _ISO_GAUSS_SIGMA_PER_CUTOFF / px_mm
    return ndimage.gaussian_filter(z, sigma_px, mode="wrap" if periodic else "reflect")


def split_bands(z: np.ndarray, px_mm: float, cutoff_mm: float) -> tuple[np.ndarray, np.ndarray]:
    """Return (macro, meso): low-pass and residual of a periodic height field."""
    macro = gaussian_lowpass(z, cutoff_mm, px_mm, periodic=True)
    return macro, z - macro


def dominant_orientation(z: np.ndarray) -> tuple[float, float]:
    """Main structure direction from the 2D FFT power spectrum.

    Returns (angle_deg, anisotropy). angle_deg is the direction in which ridges/grooves
    *run*, measured from the +x axis counter-clockwise in [0, 180); 90 = vertical.
    anisotropy in [0, 1]: 0 isotropic, 1 perfectly unidirectional.
    The spectral second moments equal the averaged gradient structure tensor (Parseval).
    """
    zz = z - z.mean()
    win = np.outer(np.hanning(z.shape[0]), np.hanning(z.shape[1]))
    power = np.abs(np.fft.fft2(zz * win)) ** 2
    ky = np.fft.fftfreq(z.shape[0]).reshape(-1, 1)
    kx = np.fft.fftfreq(z.shape[1]).reshape(1, -1)
    # Image rows run downwards; flip ky so the angle refers to y up.
    ky = -ky
    jxx = float(np.sum(power * kx * kx))
    jyy = float(np.sum(power * ky * ky))
    jxy = float(np.sum(power * kx * ky))
    tr = jxx + jyy
    if tr <= 0:
        return 0.0, 0.0
    lam_diff = math.sqrt((jxx - jyy) ** 2 + 4.0 * jxy**2)
    anisotropy = lam_diff / tr
    # Dominant *gradient* direction; structures run perpendicular to it.
    grad_angle = 0.5 * math.degrees(math.atan2(2.0 * jxy, jxx - jyy))
    struct_angle = (grad_angle + 90.0) % 180.0
    return struct_angle, anisotropy


def rotation_for_mode(struct_angle_deg: float, mode: str) -> float:
    """Counter-clockwise rotation (deg) that puts the main structure in installed position.

    auto_along_flow: structures run vertically (water flows down along them, Mustafa et al.
    2021: obstacles 'along the flow'); cross: horizontally; none: no rotation.
    """
    if mode == "none":
        return 0.0
    target = 90.0 if mode == "auto_along_flow" else 0.0
    rot = (target - struct_angle_deg) % 180.0
    return rot - 180.0 if rot > 90.0 else rot


def rotate(z: np.ndarray, angle_deg: float) -> np.ndarray:
    """Rotate counter-clockwise (y up) around the centre, keeping the shape."""
    if abs(angle_deg) < 1e-9:
        return z.copy()
    # ndimage.rotate works in image coordinates (row down), where a positive angle is
    # counter-clockwise on screen, i.e. counter-clockwise with y up as well.
    return ndimage.rotate(z, angle_deg, reshape=False, order=1, mode="nearest")


def center_crop(z: np.ndarray, fraction: float) -> np.ndarray:
    n = z.shape[0]
    k = int(round(n * fraction))
    o = (n - k) // 2
    return z[o:o + k, o:o + k]


def resample(z: np.ndarray, n: int) -> np.ndarray:
    if z.shape == (n, n):
        return z.copy()
    return ndimage.zoom(z, (n / z.shape[0], n / z.shape[1]), order=1, mode="nearest",
                        grid_mode=True)


def resample_periodic(z: np.ndarray, n: int) -> np.ndarray:
    """Resample a periodic field via the Fourier domain (keeps periodicity exactly)."""
    m = z.shape[0]
    if m == n:
        return z.copy()
    f = np.fft.fftshift(np.fft.fft2(z))
    out = np.zeros((n, n), dtype=complex)
    k = min(m, n)
    so, do = (m - k) // 2, (n - k) // 2
    out[do:do + k, do:do + k] = f[so:so + k, so:so + k]
    return np.real(np.fft.ifft2(np.fft.ifftshift(out))) * (n * n) / (m * m)


def robust_range(z: np.ndarray, lo: float = 0.5, hi: float = 99.5) -> tuple[float, float]:
    a, b = np.percentile(z, [lo, hi])
    return float(a), float(b)


def normalize_depth(z: np.ndarray, depth_mm: float) -> np.ndarray:
    """Map robust range to [-depth, 0] (0 = highest point), clipping outliers."""
    lo, hi = robust_range(z)
    if hi - lo < 1e-12 or depth_mm <= 0:
        return np.zeros_like(z)
    return np.clip((z - hi) / (hi - lo), -1.0, 0.0) * depth_mm


def normalize_zero_mean(z: np.ndarray, amplitude_mm: float) -> np.ndarray:
    """Scale so the robust peak-to-valley equals amplitude, zero mean."""
    lo, hi = robust_range(z)
    if hi - lo < 1e-12 or amplitude_mm <= 0:
        return np.zeros_like(z)
    out = np.clip(z, lo, hi) / (hi - lo) * amplitude_mm
    return out - out.mean()


def slope_angle_deg(z: np.ndarray, px_mm: float, periodic: bool = True) -> np.ndarray:
    if periodic:
        gy = (np.roll(z, -1, 0) - np.roll(z, 1, 0)) / (2 * px_mm)
        gx = (np.roll(z, -1, 1) - np.roll(z, 1, 1)) / (2 * px_mm)
    else:
        gy, gx = np.gradient(z, px_mm)
    return np.degrees(np.arctan(np.hypot(gx, gy)))


def limit_slope(z: np.ndarray, px_mm: float, max_angle_deg: float, periodic: bool = True,
                max_iter: int = 10_000) -> np.ndarray:
    """Largest surface <= z whose flank angles do not exceed max_angle_deg.

    Grey erosion with a cone (iterated 3x3 octagonal approximation) - only removes
    material from the tile (= adds it to the stamp), never deepens the relief. Steep pits
    become funnels with draft, steep ridges become ridges with draft.
    """
    if max_angle_deg >= 89.999:
        return z.copy()
    s = math.tan(math.radians(max_angle_deg)) * px_mm
    d = math.sqrt(2.0) * s
    out = z.astype(np.float64, copy=True)
    pad_mode = "wrap" if periodic else "edge"
    for _ in range(max_iter):
        p = np.pad(out, 1, mode=pad_mode)
        c = p[1:-1, 1:-1]
        cand = np.minimum.reduce([
            c,
            p[:-2, 1:-1] + s, p[2:, 1:-1] + s, p[1:-1, :-2] + s, p[1:-1, 2:] + s,
            p[:-2, :-2] + d, p[:-2, 2:] + d, p[2:, :-2] + d, p[2:, 2:] + d,
        ])
        if np.array_equal(cand, out):
            break
        out = cand
    return out


def tile_period(z_period: np.ndarray, repeats: int) -> np.ndarray:
    return np.tile(z_period, (repeats, repeats))


def seam_ratio(z: np.ndarray) -> float:
    """Mean absolute step across the periodic seams divided by the mean interior step.

    A seamless field gives ~1 (the seam behaves like any other row/column boundary);
    a non-periodic field gives values far above 1.
    """
    seam = 0.5 * (np.mean(np.abs(z[0, :] - z[-1, :])) + np.mean(np.abs(z[:, 0] - z[:, -1])))
    interior = 0.5 * (np.mean(np.abs(np.diff(z, axis=0))) + np.mean(np.abs(np.diff(z, axis=1))))
    if interior <= 1e-12:
        return 1.0 if seam <= 1e-12 else float("inf")
    return float(seam / interior)
