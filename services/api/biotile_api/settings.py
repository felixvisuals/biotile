from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", env_file_encoding="utf-8",
                                      extra="ignore")

    # Tripo
    tripo_mode: str = Field("mock", pattern="^(mock|live)$")
    tripo_api_key: SecretStr = SecretStr("")
    tripo_base_url: str = "https://openapi.tripo3d.ai/v3"
    tripo_record: bool = False
    tripo_fixtures_dir: Path = ROOT / "tests" / "fixtures" / "tripo"
    mock_task_seconds: float = 4.0

    # Infrastructure (defaults run without Docker: SQLite, local files, in-process jobs)
    database_url: str = f"sqlite:///{ROOT / 'var' / 'biotile.db'}"
    storage_backend: str = Field("local", pattern="^(local|s3)$")
    storage_dir: Path = ROOT / "var" / "storage"
    s3_endpoint_url: str | None = None
    s3_bucket: str = "biotile"
    s3_access_key: SecretStr = SecretStr("")
    s3_secret_key: SecretStr = SecretStr("")
    queue_backend: str = Field("inline", pattern="^(inline|rq)$")
    redis_url: str = "redis://localhost:6379/0"

    # Accounts & limits (enforced server side; see auth.py)
    generation_limit_mock: int = 20
    generation_limit_live: int = 3
    global_daily_generation_cap: int = 30
    registration_requires_invite: bool = True
    # Keys the invite-code HMAC. Set a long random value in .env (scripts/invites.py init).
    secret_key: SecretStr = SecretStr("dev-only-change-me")
    session_days: int = 30
    # Competition jury: one-click login into a shared jury account (no email, no invite).
    jury_login_enabled: bool = True
    jury_generation_limit: int = 10
    cookie_secure: bool = False  # set true behind HTTPS

    # App
    public_base_url: str = "http://localhost:5173"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    pipeline_internal_px: int = 2048
    pipeline_preview_px: int = 384
    max_upload_mb: int = 20
    demo_account_name: str = "BIOTILE demo"
    library_dir: Path = ROOT / "data" / "library"


@lru_cache
def get_settings() -> Settings:
    return Settings()
