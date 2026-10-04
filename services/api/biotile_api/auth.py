"""Accounts, sessions and the generation quota.

* Passwords: scrypt (stdlib), per-password salt.
* Sessions: random 32-byte token in an HttpOnly cookie; only its SHA-256 is stored.
* Quota: every Tripo generation is charged with ONE conditional UPDATE
  (`... SET used = used + 1 WHERE id = ? AND used < limit`), so parallel requests cannot
  overrun it. A global daily cap protects the credit budget across all accounts.
* Rate limits for login/registration: in-memory sliding window per IP (single process; move
  to Redis when the API runs with several workers).
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta

from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from .models import Account, AuthSession, Job, SessionLocal
from .settings import get_settings

COOKIE = "biotile_session"
_SCRYPT = {"n": 2**14, "r": 8, "p": 1}


# -- passwords ------------------------------------------------------------------------
def hash_password(pw: str) -> str:
    salt = secrets.token_bytes(16)
    h = hashlib.scrypt(pw.encode(), salt=salt, dklen=32, **_SCRYPT)
    return f"scrypt${salt.hex()}${h.hex()}"


def verify_password(pw: str, stored: str | None) -> bool:
    if not stored or not stored.startswith("scrypt$"):
        return False
    _, salt, h = stored.split("$")
    cand = hashlib.scrypt(pw.encode(), salt=bytes.fromhex(salt), dklen=32, **_SCRYPT)
    return hmac.compare_digest(cand.hex(), h)


# -- rate limiting --------------------------------------------------------------------
_hits: dict[str, deque] = defaultdict(deque)


def rate_limit(key: str, limit: int, window_s: float) -> None:
    now = time.monotonic()
    q = _hits[key]
    while q and now - q[0] > window_s:
        q.popleft()
    if len(q) >= limit:
        raise HTTPException(429, detail={"key": "errors.too_many_attempts"})
    q.append(now)


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


# -- sessions -------------------------------------------------------------------------
def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def start_session(db: Session, response: Response, account: Account) -> None:
    s = get_settings()
    token = secrets.token_urlsafe(32)
    db.add(AuthSession(token_hash=_hash_token(token), account_id=account.id,
                       expires_at=datetime.now(UTC) + timedelta(days=s.session_days)))
    db.commit()
    response.set_cookie(COOKIE, token, max_age=s.session_days * 86400, httponly=True,
                        samesite="lax", secure=s.cookie_secure, path="/")


def end_session(db: Session, request: Request, response: Response) -> None:
    token = request.cookies.get(COOKIE)
    if token:
        sess = db.get(AuthSession, _hash_token(token))
        if sess:
            db.delete(sess)
            db.commit()
    response.delete_cookie(COOKIE, path="/")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def optional_account(request: Request, db: Session = Depends(get_db)) -> Account | None:
    token = request.cookies.get(COOKIE)
    if not token:
        return None
    sess = db.get(AuthSession, _hash_token(token))
    if sess is None:
        return None
    expires = sess.expires_at if sess.expires_at.tzinfo else sess.expires_at.replace(tzinfo=UTC)
    if expires < datetime.now(UTC):
        db.delete(sess)
        db.commit()
        return None
    acc = db.get(Account, sess.account_id)
    return acc if acc and acc.is_active else None


def current_account(acc: Account | None = Depends(optional_account)) -> Account:
    if acc is None:
        raise HTTPException(401, detail={"key": "errors.login_required"})
    return acc


# -- quota ----------------------------------------------------------------------------
def limit_for(acc: Account, mode: str) -> int:
    # A per-account limit (e.g. the shared jury account) caps real Tripo generations only.
    if acc.generation_limit is not None and mode == "live":
        return acc.generation_limit
    s = get_settings()
    return s.generation_limit_live if mode == "live" else s.generation_limit_mock


def quota(acc: Account, mode: str) -> dict:
    used = acc.generations_used_live if mode == "live" else acc.generations_used_mock
    lim = limit_for(acc, mode)
    return {"mode": mode, "limit": lim, "used": used, "remaining": max(0, lim - used)}


def charge_generation(db: Session, acc: Account, mode: str) -> None:
    """Atomically take one generation from the account, or raise 429."""
    s = get_settings()
    if mode == "live":  # the global cap protects Tripo credits; simulated runs cost nothing
        since = datetime.now(UTC) - timedelta(days=1)
        today = db.scalar(select(func.count()).select_from(Job).where(
            Job.kind == "generate", Job.counted.is_(True), Job.tripo_mode == "live",
            Job.created_at >= since)) or 0
        if today >= s.global_daily_generation_cap:
            raise HTTPException(429, detail={"key": "errors.daily_cap"})
    col = Account.generations_used_live if mode == "live" else Account.generations_used_mock
    res = db.execute(update(Account).where(Account.id == acc.id, col < limit_for(acc, mode))
                     .values({col: col + 1}))
    if res.rowcount != 1:
        db.rollback()
        raise HTTPException(429, detail={"key": "errors.quota_exhausted"})
    db.commit()
    db.refresh(acc)


def charge_with_fallback(db: Session, acc: Account, mode: str) -> str:
    """Charge a generation in `mode`. When the live quota or the daily cap is used up, fall back
    to the simulated (mock) pipeline instead of refusing; returns the mode actually charged."""
    try:
        charge_generation(db, acc, mode)
        return mode
    except HTTPException:
        if mode != "live":
            raise
    charge_generation(db, acc, "mock")
    return "mock"


def refund_generation(db: Session, account_id: str, mode: str) -> None:
    """Give a generation back when it failed before Tripo accepted the task (no credits)."""
    col = Account.generations_used_live if mode == "live" else Account.generations_used_mock
    db.execute(update(Account).where(Account.id == account_id, col > 0).values({col: col - 1}))
    db.commit()


# -- invites ------------------------------------------------------------------------------
# Codes look like "K7PM-2XQH-9WTR": 12 characters from a 31-symbol alphabet without 0/O/1/I/L
# (~59 bits). Only HMAC-SHA256(SECRET_KEY, normalised code) is stored, so neither the
# frontend nor a database dump reveals usable codes; registration is rate-limited per IP.
INVITE_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"


def normalise_code(code: str) -> str:
    return "".join(ch for ch in code.upper() if ch.isalnum())


def hash_invite(code: str) -> str:
    key = get_settings().secret_key.get_secret_value().encode()
    return hmac.new(key, normalise_code(code).encode(), hashlib.sha256).hexdigest()


def generate_invite_code() -> str:
    raw = "".join(secrets.choice(INVITE_ALPHABET) for _ in range(12))
    return f"{raw[:4]}-{raw[4:8]}-{raw[8:]}"


def consume_invite(db: Session, code: str) -> bool:
    """Atomically use one invite. False if unknown, revoked, expired or used up."""
    from .models import Invite

    now = datetime.now(UTC)
    res = db.execute(update(Invite).where(
        Invite.code_hash == hash_invite(code), Invite.revoked.is_(False),
        Invite.uses < Invite.max_uses,
        (Invite.expires_at.is_(None)) | (Invite.expires_at > now),
    ).values(uses=Invite.uses + 1))
    return res.rowcount == 1
