"""Seed the gallery with reference tiles and library samples (mock mode, no credits).

Creates, generates, exports and publishes: REF-FLAT, REF-GEO and three library surfaces.
No observations are seeded: the open dataset must only contain real field data.

Run:  uv run python scripts/seed_demo.py
"""

from __future__ import annotations

import sys

from biotile_api.design_service import run_export, run_generate
from biotile_api.models import Account, Design, Job, SessionLocal, init_db
from biotile_api.settings import get_settings
from sqlalchemy import select

SEEDS = [
    ("REF-FLAT", "Glatte Vergleichskachel",
     "Eine glatte Kachel ohne Struktur. Sie zeigt, was auch ohne Relief wächst. Gehört in jede Wand."),
    ("REF-GEO", "Standard-Vergleichskachel",
     "Breite, flache Mulden und feine Rillen, die mit dem Wasser von oben nach unten laufen, nach "
     "veröffentlichten Richtwerten (Mustafa et al. 2021). Gehört in jede Wand."),
    ("tafoni", "Wabenverwitterung im Sandstein (Beispiel)",
     "Wabenartige Mulden im Sandstein, die sich selbst beschatten. Beispiel aus einem synthetischen "
     "Platzhalter-Modell."),
    ("bark", "Tiefe Rindenfurchen (Beispiel)",
     "Senkrechte Furchen wie bei alter Baumrinde. Beispiel aus einem synthetischen Platzhalter-Modell."),
    ("karren", "Regenrillen im Kalkstein (Beispiel)",
     "Rinnen, die Regen über lange Zeit in Kalkstein löst, alle bergab. Beispiel aus einem "
     "synthetischen Platzhalter-Modell."),
]

# English titles and descriptions for the German seed texts (the UI picks them by language).
EN = {
    "Glatte Vergleichskachel": ("Smooth control tile",
        "A smooth tile without texture. It shows what grows even without relief. Belongs in every wall."),
    "Standard-Vergleichskachel": ("Standard control tile",
        "Broad, shallow hollows and fine grooves that run with the water from top to bottom, following "
        "published reference values (Mustafa et al. 2021). Belongs in every wall."),
    "Wabenverwitterung im Sandstein (Beispiel)": ("Honeycomb weathering in sandstone (example)",
        "Honeycomb hollows in sandstone that shade themselves. Example from a synthetic placeholder model."),
    "Wabenverwitterung im Sandstein (Test)": ("Honeycomb weathering in sandstone (test)", None),
    "Tiefe Rindenfurchen (Beispiel)": ("Deep bark furrows (example)",
        "Vertical furrows like old tree bark. Example from a synthetic placeholder model."),
    "Regenrillen im Kalkstein (Beispiel)": ("Rain grooves in limestone (example)",
        "Channels that rain dissolves into limestone over a long time, all running downhill. Example "
        "from a synthetic placeholder model."),
    "Lavagestein": ("Lava rock", None),
    "Wurzeloberfläche": ("Root surface", None),
    "Fels": ("Rock", None),
    "Stein": ("Stone", None),
}


def backfill_english(db) -> None:
    for d in db.scalars(select(Design).where(Design.title_en.is_(None))):
        if d.title in EN:
            d.title_en, desc = EN[d.title]
            if desc and not d.description_en:
                d.description_en = desc
    db.commit()


def main() -> int:
    s = get_settings()
    init_db()
    with SessionLocal() as db:
        backfill_english(db)
    if s.tripo_mode != "mock":
        print("seed_demo only runs in TRIPO_MODE=mock (library samples use synthetic fixtures)")
        return 1
    init_db()
    with SessionLocal() as db:
        acc = db.scalar(select(Account).where(Account.name == s.demo_account_name))
        if acc is None:
            acc = Account(name=s.demo_account_name, type="project", region_coarse="Stuttgart",
                          credit_quota=500.0)
            db.add(acc)
            db.commit()
        for surface, title, desc in SEEDS:
            if db.scalar(select(Design).where(Design.surface_type == surface,
                                              Design.status == "published")):
                print(f"skip {surface}: already published")
                continue
            d = Design(title=title, description=desc, title_en=EN[title][0],
                       description_en=EN[title][1], source_type="procedural",
                       surface_type=surface, author_account_id=acc.id)
            db.add(d)
            db.commit()
            for kind, fn in (("generate", run_generate), ("export", run_export)):
                job = Job(design_id=d.id, kind=kind)
                db.add(job)
                db.commit()
                fn(job.id)
                db.refresh(job)
                if job.status != "success":
                    print(f"{surface}: {kind} failed: {job.error}")
                    return 1
            db.refresh(d)
            d.status = "published"
            db.commit()
            print(f"published {d.code} {title}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
