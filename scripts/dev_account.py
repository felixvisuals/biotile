"""Create a local test account for development (credentials go to var/dev_account.txt).

    uv run python scripts/dev_account.py
"""

import secrets
from pathlib import Path

from biotile_api.auth import hash_password
from biotile_api.models import Account, SessionLocal, init_db
from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
EMAIL = "dev-school@example.org"

init_db()
with SessionLocal() as db:
    pw = secrets.token_urlsafe(12)
    acc = db.scalar(select(Account).where(Account.email == EMAIL))
    if acc is None:
        acc = Account(name="Dev School", email=EMAIL, type="school")
        db.add(acc)
    acc.password_hash = hash_password(pw)
    db.commit()
out = ROOT / "var" / "dev_account.txt"
out.parent.mkdir(exist_ok=True)
out.write_text(f"email={EMAIL}\npassword={pw}\n")
out.chmod(0o600)
print(f"test account ready, credentials in {out.relative_to(ROOT)}")
