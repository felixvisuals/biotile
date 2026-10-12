"""Example tile locations in Barcelona for the map (demo data, clearly marked as such).

Idempotent: existing demo spots are updated in place (position, orientation, photo), missing
ones are added. A spot's photo is a mock-up of the real place with the tiles added by AI image
editing; it lives in data/demo_sites/<file>. To give another spot a photo, drop the JPEG there
and put its file name into the last column below.

    uv run python scripts/seed_barcelona.py
"""

import hashlib
import io
from pathlib import Path

from biotile_api.models import Account, Design, Instance, SessionLocal, init_db
from biotile_api.storage import get_storage
from PIL import Image
from sqlalchemy import func, select

TAG = "Beispielstandort (Demo) · example location"
PHOTOS = Path(__file__).resolve().parents[1] / "data" / "demo_sites"

# place (also matches older seeds), latitude, longitude, facing in degrees, photo file or None
SPOTS = [
    ("Passeig de Gràcia", 41.3917, 2.1649, 0, None),
    ("Parc de la Ciutadella", 41.38632, 2.18537, 20, "ciutadella.jpg"),        # Passeig de Picasso 21
    ("Park Güell", 41.4145, 2.1527, 340, None),
    ("Sagrada Família", 41.40319, 2.17482, 10, "sagrada_familia.jpg"),        # Carrer de Mallorca 401
    ("Montjuïc", 41.3634, 2.1586, 355, None),
    ("Barceloneta", 41.3797, 2.1890, 30, None),
    ("Gràcia, Plaça del Sol", 41.4022, 2.1567, 0, "gracia_placa_del_sol.jpg"),
    ("Poblenou", 41.4035, 2.2007, 15, None),
    ("Diagonal Mar, Carrer dels Ferrers", 41.40532, 2.21059, 340, "ferrers.jpg"),
    ("Ciutat Vella, Passeig de Circumval·lació", 41.38706, 2.19233, 300, "circumvallacio.jpg"),
]


def store_photo(file: str) -> str:
    """Store the photo content-addressed (like observation photos) and return its key."""
    im = Image.open(PHOTOS / file).convert("RGB")
    im.thumbnail((1600, 1600), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=82, optimize=True)
    data = buf.getvalue()
    sha = hashlib.sha256(data).hexdigest()
    return get_storage().put(f"sites/{sha[:2]}/{sha}.jpg", data, "image/jpeg")


def main() -> None:
    init_db()
    with SessionLocal() as db:
        acc = db.scalar(select(Account).where(Account.name == "BIOTILE demo"))
        designs = [d for d in db.scalars(select(Design).where(Design.status == "published"))
                   if d.code and not (d.surface_type or "").startswith("REF-")]
        existing = {i.location_coarse: i for i in db.scalars(select(Instance).where(Instance.notes == TAG))}
        for k, (place, lat, lon, deg, photo) in enumerate(SPOTS):
            coarse = f"Barcelona, {place}"
            inst = existing.get(coarse)
            if inst is None:
                d = designs[k % len(designs)]
                n = (db.scalar(select(func.count()).select_from(Instance).where(Instance.design_id == d.id)) or 0) + 1
                base = "BT-" + d.code.removeprefix("BT-D-").removeprefix("BT-")
                inst = Instance(id=f"{base}-{n:03d}", design_id=d.id, account_id=acc.id if acc else None,
                                material="clay", process="press_mould", booster=True,
                                location_coarse=coarse, geo_visibility="exact", mounting_adapter="wall", notes=TAG)
                db.add(inst)
                action = "added"
            else:
                action = "updated"
            inst.geo_lat, inst.geo_lon, inst.orientation_deg = lat, lon, deg
            inst.site_photo_key = store_photo(photo) if photo else None
            db.commit()
            print(f"{action:8s} {inst.id}  {place}{'  + photo' if photo else ''}")


if __name__ == "__main__":
    main()
