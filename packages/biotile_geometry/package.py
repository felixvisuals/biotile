"""Tool package (brief 8.2 step 19): ZIP with STL/3MF, height field, renders, PDFs, design.json."""

from __future__ import annotations

import io
import json
import zipfile

import numpy as np
from PIL import Image

from . import constants as C
from .pdfs import instructions, preview_image, reference_card
from .pipeline import TileResult, design_json, wall_field
from .tools import ToolSet, lay_flat

HEIGHT_PNG_RANGE_MM = 25.0  # 16-bit PNG: 0 = 25 mm deep, 65535 = reference plane


def heightfield_png16(front: np.ndarray) -> bytes:
    v = np.clip(1.0 + front / HEIGHT_PNG_RANGE_MM, 0.0, 1.0)
    im = Image.fromarray((v * 65535).round().astype(np.uint16))
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()


def png_bytes(im: Image.Image) -> bytes:
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()


def bands_image(result: TileResult, size: int = 512) -> Image.Image:
    """Macro | meso | final, side by side (asset board: band decomposition)."""
    def norm(a: np.ndarray) -> Image.Image:
        a = (a - a.min()) / (np.ptp(a) + 1e-9)
        return Image.fromarray((a * 255).astype(np.uint8)).resize((size, size))

    out = Image.new("L", (size * 3 + 20, size), 255)
    for i, a in enumerate((result.macro, result.meso, result.front)):
        out.paste(norm(a), (i * (size + 10), 0))
    return out


def build_package(design_id: str, result: TileResult, tools: ToolSet, metrics: dict,
                  extra_meta: dict | None = None) -> bytes:
    preview = png_bytes(preview_image(result.front, result.px_mm, mask=result.mask))
    meta = {"design_id": design_id, "metrics": metrics, "bed_checks": tools.bed_checks,
            "heightfield_png_range_mm": HEIGHT_PNG_RANGE_MM}
    if extra_meta:
        meta.update(extra_meta)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("design.json", design_json(result, meta))
        for name, mesh in tools.parts.items():
            flat = lay_flat(mesh, name)
            z.writestr(f"stl/{name}.stl", flat.export(file_type="stl"))
            z.writestr(f"3mf/{name}.3mf", flat.export(file_type="3mf"))
        z.writestr("heightfield/front_16bit.png", heightfield_png16(result.front))
        npy = io.BytesIO()
        np.save(npy, result.front.astype(np.float32))
        z.writestr("heightfield/front_mm.npy", npy.getvalue())
        z.writestr("renders/preview.png", preview)
        wall, wall_px = wall_field(result, 1200)
        z.writestr("renders/preview_wall.png", png_bytes(preview_image(wall, wall_px)))
        z.writestr("renders/bands_macro_meso_final.png", png_bytes(bands_image(result)))
        z.writestr("docs/instructions.pdf",
                   instructions(design_id, result.params.to_dict(),
                                [c.to_dict() for c in result.checks], tools.bed_checks, preview))
        z.writestr("docs/reference_card_blank.pdf", reference_card())
        z.writestr("LICENSE-DESIGN.txt",
                   "This design and the generated tool geometry are licensed under CC BY-SA 4.0.\n"
                   "https://creativecommons.org/licenses/by-sa/4.0/\n")
        z.writestr("README.txt", _readme(design_id))
    return buf.getvalue()


def _readme(design_id: str) -> str:
    return (f"BIOTILE {design_id}\n\n"
            "stl/ and 3mf/: printable parts, already in print orientation.\n"
            "  matrix          relief up (matrix) or relief down (stamp) - same part\n"
            "  frame_*         casting frame (square: 4 walls, hexagon: 2 halves), on the pins\n"
            "  backplate       presses the back flat; guide bosses for the hanging holes\n"
            "  hole_punch      makes the two slanted hanging holes through the guides\n"
            "heightfield/: finished front, 16-bit PNG and float32 NPY in mm (0 = reference plane)\n"
            "docs/instructions.pdf: process steps, checks, print settings\n"
            "docs/reference_card_blank.pdf: hold into every monitoring photo\n"
            f"pipeline {C.PIPELINE_VERSION}\n")


def summary_json(result: TileResult, tools: ToolSet) -> str:
    return json.dumps({"checks": [c.to_dict() for c in result.checks], "bed": tools.bed_checks})
