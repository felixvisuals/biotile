"""Manage registration invite codes (server side only).

    uv run python scripts/invites.py init                      # create SECRET_KEY in .env
    uv run python scripts/invites.py create --note "School X" --uses 1 --days 60 [--count 5]
    uv run python scripts/invites.py list
    uv run python scripts/invites.py revoke <invite-id>

Codes are printed ONCE. The database only keeps an HMAC of each code (keyed with
SECRET_KEY), so codes cannot be read back from the database or the frontend.
Changing SECRET_KEY invalidates all existing codes.
"""

from __future__ import annotations

import argparse
import secrets
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def cmd_init() -> int:
    env = ROOT / ".env"
    text = env.read_text() if env.exists() else ""
    lines = [ln for ln in text.splitlines() if not ln.startswith("SECRET_KEY=")]
    if any(ln.startswith("SECRET_KEY=") and "dev-only" not in ln for ln in text.splitlines()):
        print("SECRET_KEY already set in .env (left unchanged)")
        return 0
    lines.append(f"SECRET_KEY={secrets.token_urlsafe(48)}")
    env.write_text("\n".join(lines) + "\n")
    env.chmod(0o600)
    print("SECRET_KEY written to .env")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    c = sub.add_parser("create")
    c.add_argument("--note", default=None)
    c.add_argument("--uses", type=int, default=1)
    c.add_argument("--days", type=int, default=60)
    c.add_argument("--count", type=int, default=1)
    c.add_argument("--code", default=None, help="use this code instead of a random one")
    sub.add_parser("list")
    r = sub.add_parser("revoke")
    r.add_argument("invite_id")
    args = ap.parse_args()
    if args.cmd == "init":
        return cmd_init()

    from biotile_api.auth import generate_invite_code, hash_invite
    from biotile_api.models import Invite, SessionLocal, init_db
    from biotile_api.settings import get_settings

    if "dev-only" in get_settings().secret_key.get_secret_value():
        print("Refusing: SECRET_KEY is the dev default. Run: python scripts/invites.py init")
        return 1
    init_db()
    with SessionLocal() as db:
        if args.cmd == "create":
            exp = datetime.now(UTC) + timedelta(days=args.days) if args.days else None
            for _ in range(args.count):
                code = args.code or generate_invite_code()
                inv = Invite(code_hash=hash_invite(code), note=args.note, max_uses=args.uses,
                             expires_at=exp)
                db.add(inv)
                db.commit()
                print(f"{code}   (id {inv.id}, uses {args.uses}, expires {exp:%Y-%m-%d})")
        elif args.cmd == "list":
            for inv in db.query(Invite).order_by(Invite.created_at):
                state = "revoked" if inv.revoked else f"{inv.uses}/{inv.max_uses} used"
                print(f"{inv.id}  {inv.note or '-':30s} {state:14s} expires {inv.expires_at}")
        elif args.cmd == "revoke":
            inv = db.get(Invite, args.invite_id)
            if inv is None:
                print("not found")
                return 1
            inv.revoked = True
            db.commit()
            print("revoked")
    return 0


if __name__ == "__main__":
    sys.exit(main())
