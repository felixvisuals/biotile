"""PDF documents: reference card (brief 10) and tool-package instructions."""

from __future__ import annotations

import io

import numpy as np
from PIL import Image
from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib.colors import Color, black, white
from reportlab.lib.pagesizes import A4, A5
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from . import constants as C

ARUCO_DICT = "DICT_4X4_50"
ARUCO_IDS = (0, 1, 2, 3)  # top-left, top-right, bottom-right, bottom-left
ARUCO_SIZE_MM = 18.0
CARD_SWATCHES = [  # name, sRGB 0..1
    ("white", (1.0, 1.0, 1.0)), ("grey 18%", (0.46, 0.46, 0.46)), ("black", (0.0, 0.0, 0.0)),
    ("red", (0.8, 0.1, 0.1)), ("green", (0.1, 0.6, 0.2)), ("blue", (0.1, 0.2, 0.75)),
    ("moss green", (0.33, 0.45, 0.18)),
]


def aruco_image(marker_id: int, px: int = 240) -> Image.Image:
    import cv2

    d = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, ARUCO_DICT))
    img = cv2.aruco.generateImageMarker(d, marker_id, px)
    return Image.fromarray(img)


def _img(c: canvas.Canvas, im: Image.Image, x: float, y: float, w: float, h: float) -> None:
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    buf.seek(0)
    c.drawImage(ImageReader(buf), x, y, w, h)


def reference_card(instance_id: str | None = None, url: str | None = None) -> bytes:
    """A5 landscape card held into every monitoring photo: 4 ArUco markers (perspective and
    scale), colour patches incl. 18 % grey (white balance), 50 mm scale bar, QR code."""
    buf = io.BytesIO()
    w, h = A5[1], A5[0]
    c = canvas.Canvas(buf, pagesize=(w, h))
    c.setTitle("BIOTILE reference card")
    m = 8 * mm
    a = ARUCO_SIZE_MM * mm
    for mid, (x, y) in zip(ARUCO_IDS, [(m, h - m - a), (w - m - a, h - m - a), (w - m - a, m),
                                      (m, m)]):
        _img(c, aruco_image(mid), x, y, a, a)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(m + a + 6 * mm, h - m - 7 * mm, "BIOTILE reference card")
    c.setFont("Helvetica", 8)
    c.drawString(m + a + 6 * mm, h - m - 12 * mm,
                 f"ArUco {ARUCO_DICT} ids 0-3, {ARUCO_SIZE_MM:g} mm. Hold flat next to the tile, "
                 "diffuse light, no people.")
    # Colour patches
    sw = 17 * mm
    x0 = m + a + 6 * mm
    y0 = h - m - 36 * mm
    for i, (name, rgb) in enumerate(CARD_SWATCHES):
        c.setFillColor(Color(*rgb))
        c.setStrokeColor(black)
        c.rect(x0 + i * (sw + 1.5 * mm), y0, sw, sw, fill=1, stroke=1)
        c.setFillColor(black)
        c.setFont("Helvetica", 6)
        c.drawString(x0 + i * (sw + 1.5 * mm), y0 - 3 * mm, name)
    # Scale bar 50 mm, alternating 10 mm blocks
    yb = y0 - 14 * mm
    for i in range(5):
        c.setFillColor(black if i % 2 == 0 else white)
        c.rect(x0 + i * 10 * mm, yb, 10 * mm, 4 * mm, fill=1, stroke=1)
    c.setFillColor(black)
    c.setFont("Helvetica", 7)
    c.drawString(x0, yb - 3.5 * mm, "0")
    c.drawString(x0 + 48 * mm, yb - 3.5 * mm, "50 mm")
    # Fields
    c.setFont("Helvetica", 9)
    fy = m + 24 * mm
    c.drawString(x0, fy, "Instance ID:")
    c.line(x0 + 22 * mm, fy - 1, x0 + 95 * mm, fy - 1)
    if instance_id:
        c.setFont("Helvetica-Bold", 11)
        c.drawString(x0 + 24 * mm, fy + 1, instance_id)
        c.setFont("Helvetica", 9)
    c.drawString(x0, fy - 10 * mm, "Date:")
    c.line(x0 + 22 * mm, fy - 10 * mm - 1, x0 + 95 * mm, fy - 10 * mm - 1)
    if url:
        q = QrCodeWidget(url)
        b = q.getBounds()
        size = 34 * mm
        d = Drawing(size, size, transform=[size / (b[2] - b[0]), 0, 0, size / (b[3] - b[1]), 0,
                                           0])
        d.add(q)
        renderPDF.draw(d, c, w - m - a - size - 6 * mm, m + 4 * mm)
    c.showPage()
    c.save()
    return buf.getvalue()


def _hillshade(z: np.ndarray, px_mm: float) -> np.ndarray:
    gy, gx = np.gradient(z, px_mm)
    az, alt = np.radians(315.0), np.radians(40.0)
    slope = np.arctan(np.hypot(gx, gy))
    aspect = np.arctan2(-gx, gy)
    shade = np.sin(alt) * np.cos(slope) + np.cos(alt) * np.sin(slope) * np.cos(az - aspect)
    return np.clip(shade, 0, 1)


def preview_image(front: np.ndarray, px_mm: float, tiles: int = 1, size: int = 768,
                  mask: np.ndarray | None = None) -> Image.Image:
    """Soft monochrome hillshade (deep = darker), for galleries and PDFs. With a mask the
    outside becomes transparent (hexagonal tiles)."""
    from scipy import ndimage

    z = np.tile(front, (tiles, tiles))
    ny, nx = z.shape
    k = size / max(ny, nx)
    if k < 1:  # downsample first: avoids aliasing grain from the 2048 px raster
        z = ndimage.zoom(ndimage.gaussian_filter(z, 0.5 / k), k, order=1)
    px = px_mm * ny / z.shape[0]
    shade = _hillshade(z * 0.6, px)
    depth = (z - z.min()) / (np.ptp(z) + 1e-9)
    # Monochrome, paper-like (matches the web UI): light from top-left, deep = darker.
    v = np.clip(0.30 + 0.62 * shade + 0.10 * depth, 0, 1)
    rgb = (np.stack([v * 0.96, v * 0.96, v * 0.93], axis=-1) * 255).astype(np.uint8)
    out_w = size if nx >= ny else int(round(size * nx / ny))
    out_h = size if ny >= nx else int(round(size * ny / nx))
    if mask is None:
        return Image.fromarray(rgb).resize((out_w, out_h), Image.LANCZOS)
    m = np.tile(mask, (tiles, tiles)).astype(np.float32)
    m = ndimage.zoom(m, (z.shape[0] / m.shape[0], z.shape[1] / m.shape[1]), order=1)
    alpha = (np.clip(m, 0, 1) * 255).astype(np.uint8)
    return Image.fromarray(np.dstack([rgb, alpha]), "RGBA").resize((out_w, out_h), Image.LANCZOS)


def instructions(design_id: str, params: dict, checks: list[dict], bed: dict, preview_png: bytes
                 ) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    m = 18 * mm
    c.setTitle(f"BIOTILE {design_id} tool package")
    c.setFont("Helvetica-Bold", 18)
    c.drawString(m, h - m, f"BIOTILE {design_id}: tool package")
    c.setFont("Helvetica", 9)
    c.drawString(m, h - m - 6 * mm,
                 f"pipeline {C.PIPELINE_VERSION} · interface {C.INTERFACE_VERSION} · designs CC BY-SA 4.0")
    c.drawImage(ImageReader(io.BytesIO(preview_png)), w - m - 60 * mm, h - m - 68 * mm, 60 * mm,
                60 * mm)
    y = h - m - 16 * mm
    lines = [
        ("Parameters", None),
        (f"material {params['material']} · process {params['process']} · tool {params['tool_material']}",
         None),
        (f"macro {params['macro_depth_mm']} mm · meso {params['meso_depth_mm']} mm · edge "
         f"{params['edge_mode']} · period {params['texture_period_mm']} mm", None),
        (f"shape {params['shape']} · size {params['tile_size_mm']} mm · moss starter "
         f"{params['functional']['template']} · front code {'yes' if params['front_code'] else 'no'}",
         None),
        (f"clay shrinkage {params['shrink_pct'] if params['material'] == 'clay' else 0} % "
         "(measure on a test bar!)", None),
        ("", None),
        ("Checks", None),
    ] + [(f"[{ch['status'].upper()}] {ch['id']}: {ch['value']} (limit {ch['limit']})", None)
         for ch in checks] + [("", None), ("Printing", None)] + [
        (f"{k}: {'fits' if v['fits'] else 'DOES NOT FIT'} "
         f"{'(rotate ' + str(v['rotation_deg']) + ' deg)' if v['fits'] and v['rotation_deg'] else ''}"
         f" · {v['extent_mm']} mm", None) for k, v in bed.items()] + [
        ("Matrix: 0.08-0.12 mm layer height (layer lines add a horizontal anisotropy).", None),
        ("Prefer rPETG where available; PLA is fine for clay.", None),
        ("", None),
        ("Clay - press moulding (stage 1, classroom)", None),
        ("1 Dust matrix with corn starch or talc. 2 Place frame walls on the flange (pins!).", None),
        ("3 Lay a clay slab, work it in from the back with fingers / rolling pin.", None),
        ("4 Add extra clay on the two pad marks, press the back plate down onto the frame:", None),
        ("  it levels the rim and two solid pads. Cut off clay along the frame top.", None),
        ("5 Leather-hard: push the hole punch through both guide bosses up to the collar", None),
        ("  (slanted hanging holes). 6 Punch the ID through the window. 7 Dry slowly, fire.", None),
        ("Hanging: two stainless pins (6 mm) on the wall adapter, tilted 40 deg upwards.", None),
        ("", None),
        ("Concrete - matrix down (stage 2, workshop)", None),
        ("Release agent: rapeseed oil, NO silicone spray (hydrophobic film, Mustafa et al. 2021).", None),
        ("Surface retarder on the matrix, fine-mortar facing (sand 0-2 mm), then coarse backfill;", None),
        ("demould, wash out the retarded skin (Veeger et al. 2021). Gloves + goggles: alkaline.", None),
        ("", None),
        ("Plastic is a tool, never habitat. No printed part stays outdoors.", None),
    ]
    for text, _ in lines:
        bold = text in ("Parameters", "Checks", "Printing") or text.startswith(("Clay -", "Concrete -"))
        c.setFont("Helvetica-Bold" if bold else "Helvetica", 10 if bold else 8.5)
        c.drawString(m, y, text)
        y -= 5 * mm
        if y < m:
            c.showPage()
            y = h - m
    c.showPage()
    c.save()
    return buf.getvalue()
