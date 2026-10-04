"""Fetch surface photos for the "Nature did it first" gallery from Wikimedia Commons.

Only files whose licence is Public Domain or CC0 are accepted (free to use, no attribution
required; we still list source and author on the Credits page). Results:
    apps/web/public/images/surfaces/surface-XX.jpg
    apps/web/src/data/surface-credits.json

Run:  uv run python scripts/fetch_surface_images.py
"""

from __future__ import annotations

import io
import json
import re
import time
from pathlib import Path

import httpx
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "apps" / "web" / "public" / "images" / "surfaces"
CREDITS = ROOT / "apps" / "web" / "src" / "data" / "surface-credits.json"
API = "https://commons.wikimedia.org/w/api.php"
UA = {"User-Agent": "BIOTILE/0.3 (open-source hackathon project; surface gallery)"}
OK_LICENSES = ("cc0", "public domain", "pd")

QUERIES = [
    ("Tree bark", "Poly Haven bark diff|tree bark texture closeup"),
    ("Moss on stone", "moss on rock closeup|moss covered rock|moss on stone"),
    ("Lichen on rock", "lichen on rock texture|crustose lichen rock"),
    ("Tafoni", "tafoni|honeycomb weathering|alveolar weathering"),
    ("Dry stone wall", "dry stone wall moss|Poly Haven stone wall diff"),
    ("Karren", "karren limestone solution grooves|limestone pavement grikes|lapiaz limestone"),
    ("Plane tree bark", "plane tree bark|platanus bark|sycamore bark"),
    ("Weathered sandstone", "weathered sandstone closeup|sandstone erosion texture|sandstone texture"),
    ("Moss cushion", "moss cushion macro|moss closeup|bryophyte macro"),
    ("Old brick wall", "old brick wall moss|Poly Haven mossy brick diff"),
    ("Travertine", "travertine texture"),
    ("Lava rock", "scoria closeup|vesicular basalt|pumice texture|lava rock texture"),
    ("Forest floor roots", "Poly Haven forest ground roots diff|mossy tree roots"),
]


def _license_ok(meta: dict) -> bool:
    lic = (meta.get("LicenseShortName", {}).get("value") or "").lower()
    return any(lic.startswith(x) or x in lic for x in OK_LICENSES) and "cc-by" not in lic \
        and "cc by" not in lic


def _strip_html(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s or "").strip()


def _get(client: httpx.Client, url: str, **kw) -> httpx.Response:
    for attempt in range(6):
        r = client.get(url, **kw)
        if r.status_code != 429:
            r.raise_for_status()
            return r
        time.sleep(5 * (attempt + 1))  # polite back-off
    r.raise_for_status()
    return r


def search(client: httpx.Client, query: str) -> list[dict]:
    time.sleep(1.5)
    r = _get(client, API, params={
        "action": "query", "format": "json", "generator": "search", "gsrsearch": f"filetype:bitmap {query}",
        "gsrnamespace": 6, "gsrlimit": 30, "prop": "imageinfo",
        "iiprop": "url|extmetadata|size|mime", "iiurlwidth": 1000,
    })
    pages = (r.json().get("query") or {}).get("pages") or {}
    return sorted(pages.values(), key=lambda p: p.get("index", 0))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    CREDITS.parent.mkdir(parents=True, exist_ok=True)
    credits = []
    used: set[str] = set()
    with httpx.Client(headers=UA, timeout=60, follow_redirects=True) as client:
        for i, (label, query) in enumerate(QUERIES, start=1):
            chosen = None
            candidates = [pg for q in query.split("|") for pg in search(client, q)]
            for page in candidates:
                info = (page.get("imageinfo") or [{}])[0]
                meta = info.get("extmetadata") or {}
                if page["title"] in used or info.get("mime") not in ("image/jpeg", "image/png"):
                    continue
                t = page["title"].lower()
                # texture-map variants are data, not photos; keep only colour (diff) images
                if re.search(r"[ _(](disp|ao|nor|nor_gl|nor_dx|rough|arm|spec|mask|height|bump)[ _)]", t):
                    continue
                if any(x in t for x in ("flag", "people", "canyon", "honeycombweatheringcambrian",
                                        "mossy sandstone diff", "bark platanus diff",
                                        "seaworn sandstone brick", "landscape", "panorama", "study",
                                        "painting", "tidemand", "drawing")):
                    continue
                if not _license_ok(meta) or info.get("width", 0) < 1000:
                    continue
                chosen = (page, info, meta)
                break
            if chosen is None:
                print(f"{label}: no PD/CC0 image found")
                continue
            page, info, meta = chosen
            used.add(page["title"])
            data = _get(client, info["thumburl"]).content
            im = Image.open(io.BytesIO(data)).convert("RGB")
            # portrait crop 3:4 for the parallax columns
            w, h = im.size
            tw = min(w, int(h * 0.75))
            th = min(h, int(tw / 0.75))
            left, top = (w - tw) // 2, (h - th) // 2
            im = im.crop((left, top, left + tw, top + th)).resize((750, 1000), Image.LANCZOS)
            name = f"surface-{len(credits) + 1:02d}.jpg"
            im.save(OUT / name, quality=82, optimize=True, progressive=True)
            credits.append({
                "file": name, "label": label, "title": page["title"].removeprefix("File:"),
                "source": info.get("descriptionurl"),
                "author": _strip_html(meta.get("Artist", {}).get("value", ""))[:120] or "unknown",
                "license": meta.get("LicenseShortName", {}).get("value", ""),
            })
            print(f"{name}: {label} · {credits[-1]['license']} · {credits[-1]['title'][:60]}")
    CREDITS.write_text(json.dumps(credits, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
