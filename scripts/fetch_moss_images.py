"""Fetch the step photos of the moss starter guide (/moss-starter).

Same rules as fetch_template_images.py: Wikimedia Commons, Public Domain or CC0 only.
    apps/web/public/images/moss/<step>.jpg   and   apps/web/src/data/moss-credits.json

Run:  uv run python scripts/fetch_moss_images.py [step ...]
"""

from __future__ import annotations

import sys

import fetch_template_images as ft

ft.OUT = ft.ROOT / "apps" / "web" / "public" / "images" / "moss"
ft.CREDITS = ft.ROOT / "apps" / "web" / "src" / "data" / "moss-credits.json"
ft.REUSE = {}
ft.QUERIES = {
    "paper": "egg carton|egg cartons recycled paper|paper pulp",
    "collect": "moss between paving stones|moss in pavement cracks|moss cobblestones",
    "mix": "garden soil closeup|soil in hands|potting soil",
    "press": "moss cushion closeup|bryum moss|moss closeup",
    "water": "moss with water droplets|wet moss closeup|dew on moss",
}
ft.PICK = {"collect": "Japan Moss Path (14156130903).jpg", "mix": "Germination and humus.jpg"}

if __name__ == "__main__":
    ft.main(sys.argv[1:])
