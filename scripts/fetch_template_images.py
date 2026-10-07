"""Fetch one photo of the real surface for every template in the catalogue.

Same rules as fetch_surface_images.py: Wikimedia Commons, Public Domain or CC0 only; source and
author are listed on the Credits page. Where a gallery photo already shows the surface it is
reused. Results:
    apps/web/public/images/templates/<template-id>.jpg   (800 x 800)
    apps/web/src/data/template-credits.json

Run:  uv run python scripts/fetch_template_images.py [template-id ...]
"""

from __future__ import annotations

import io
import json
import re
import sys
from pathlib import Path

import httpx
from fetch_surface_images import CREDITS as SURFACE_CREDITS
from fetch_surface_images import OUT as SURFACE_DIR
from fetch_surface_images import UA, _get, _license_ok, _strip_html, search
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "apps" / "web" / "public" / "images" / "templates"
CREDITS = ROOT / "apps" / "web" / "src" / "data" / "template-credits.json"

# template id -> gallery photo that already shows it
REUSE = {
    "bark": "surface-01.jpg", "karren": "surface-05.jpg", "plane_bark": "surface-06.jpg",
    "sandstone": "surface-07.jpg", "travertine": "surface-10.jpg", "lava_rock": "surface-11.jpg",
}
QUERIES = {
    "weathered_rock": "lichen covered rock closeup|weathered stone surface texture|rock surface texture",
    "dry_cracked_loam": "dried mud cracks|mud cracks|desiccation cracks",
    "deadwood": "rotten wood closeup|decaying log texture|dead wood bark beetle galleries",
    "slate": "slate rock closeup|slate texture closeup|slate outcrop cleavage",
    "tafoni": "tafoni|tafone|honeycomb weathering|alveolar erosion sandstone|Wabenverwitterung",
    "vine_bark": "grapevine trunk closeup|vine stock bark|Vitis vinifera trunk",
    "mortar_joint": "old brick wall texture|brickwork texture|brick wall closeup",
    "shell_limestone": "coquina limestone|fossil shells limestone|shell limestone",
    "asphalt_cracks": "asphalt crack closeup|cracked pavement texture|road surface cracks",
    "frost_brick": "spalled brick|brick spalling|eroded brick closeup",
    "root_surface": "tree roots closeup|exposed tree roots|beech roots",
}
# chosen by hand where the search ranks unsuitable pictures first
PICK = {
    "vine_bark": "Grapevine trunk post curetage.jpg",
    "frost_brick": "Interesting brick erosion on Cherry Street, 2014 03 25 (1).jpg",
    "slate": "Cleavage and joints in Slate ggk00901.jpg",
    "tafoni": "Honeycomb Rock.jpg",
}
SKIP = re.compile(r"[ _(](disp|ao|nor|nor_gl|nor_dx|rough|arm|spec|mask|height|bump)[ _)]|"
                  r"map|diagram|painting|drawing|people|portrait|flag|logo|panorama|street|building|house|"
                  r"department|firehouse|station|church|men |man |woman|women|aerial", re.I)


def square(im: Image.Image, size: int = 800) -> Image.Image:
    w, h = im.size
    s = min(w, h)
    return im.crop(((w - s) // 2, (h - s) // 2, (w + s) // 2, (h + s) // 2)).resize((size, size), Image.LANCZOS)


def main(only: list[str]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    credits = json.loads(CREDITS.read_text()) if CREDITS.exists() else {}
    gallery = {c["file"]: c for c in json.loads(SURFACE_CREDITS.read_text())}
    for tid, file in REUSE.items():
        if only and tid not in only:
            continue
        square(Image.open(SURFACE_DIR / file).convert("RGB")).save(OUT / f"{tid}.jpg", quality=82, optimize=True)
        credits[tid] = {k: v for k, v in gallery[file].items() if k != "file"}
        print(f"{tid}: reused {file}")
    used = {c["title"] for c in credits.values()}
    with httpx.Client(headers=UA, timeout=60, follow_redirects=True) as client:
        for tid, query in QUERIES.items():
            if only and tid not in only:
                continue
            chosen = None
            pages = (pg for q in query.split("|") for pg in search(client, q))
            if tid in PICK:
                r = _get(client, "https://commons.wikimedia.org/w/api.php", params={
                    "action": "query", "format": "json", "titles": f"File:{PICK[tid]}", "prop": "imageinfo",
                    "iiprop": "url|extmetadata|size|mime", "iiurlwidth": 1000})
                pages = iter((r.json()["query"]["pages"]).values())
                used.discard(PICK[tid])
            for page in pages:
                info = (page.get("imageinfo") or [{}])[0]
                meta = info.get("extmetadata") or {}
                title = page["title"].removeprefix("File:")
                if title in used or info.get("mime") not in ("image/jpeg", "image/png") or (
                        tid not in PICK and SKIP.search(title)):
                    continue
                if not _license_ok(meta) or min(info.get("width", 0), info.get("height", 0)) < 700:
                    continue
                chosen = (title, info, meta)
                break
            if chosen is None:
                print(f"{tid}: no PD/CC0 image found")
                continue
            title, info, meta = chosen
            used.add(title)
            im = Image.open(io.BytesIO(_get(client, info["thumburl"]).content)).convert("RGB")
            square(im).save(OUT / f"{tid}.jpg", quality=82, optimize=True)
            credits[tid] = {
                "label": tid, "title": title, "source": info.get("descriptionurl"),
                "author": _strip_html(meta.get("Artist", {}).get("value", ""))[:120] or "unknown",
                "license": meta.get("LicenseShortName", {}).get("value", ""),
            }
            print(f"{tid}: {credits[tid]['license']} · {title[:70]}")
    CREDITS.write_text(json.dumps(credits, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main(sys.argv[1:])
