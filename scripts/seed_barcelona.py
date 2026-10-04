"""Example tile locations in Barcelona for the map (demo data, clearly marked as such).

    uv run python scripts/seed_barcelona.py
"""

from biotile_api.models import Account, Design, Instance, SessionLocal, init_db
from sqlalchemy import func, select

TAG = "Beispielstandort (Demo) · example location"
SPOTS = [
    ("Passeig de Gràcia", 41.3917, 2.1649, 0),
    ("Parc de la Ciutadella", 41.3881, 2.1873, 20),
    ("Park Güell", 41.4145, 2.1527, 340),
    ("Sagrada Família", 41.4036, 2.1744, 10),
    ("Montjuïc", 41.3634, 2.1586, 355),
    ("Barceloneta", 41.3797, 2.1890, 30),
    ("Gràcia, Plaça del Sol", 41.4022, 2.1567, 0),
    ("Poblenou", 41.4035, 2.2007, 15),
]

init_db()
with SessionLocal() as db:
    if db.scalar(select(func.count()).select_from(Instance).where(Instance.notes == TAG)):
        print("already seeded")
        raise SystemExit(0)
    acc = db.scalar(select(Account).where(Account.name == "BIOTILE demo"))
    designs = [d for d in db.scalars(select(Design).where(Design.status == "published"))
               if d.code and not (d.surface_type or "").startswith("REF-")]
    for k, (place, lat, lon, deg) in enumerate(SPOTS):
        d = designs[k % len(designs)]
        n = (db.scalar(select(func.count()).select_from(Instance).where(Instance.design_id == d.id)) or 0) + 1
        base = "BT-" + d.code.removeprefix("BT-D-").removeprefix("BT-")
        db.add(Instance(id=f"{base}-{n:03d}", design_id=d.id, account_id=acc.id if acc else None,
                        material="clay", process="press_mould", orientation_deg=deg, booster=True,
                        location_coarse=f"Barcelona, {place}", geo_lat=lat, geo_lon=lon,
                        geo_visibility="exact", mounting_adapter="wall", notes=TAG))
        db.commit()
        print(f"{base}-{n:03d}  {place}")
