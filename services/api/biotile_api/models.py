"""Data model (brief section 9). MVP uses a subset of the fields, all columns exist already."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

JSONType = JSON().with_variant(JSONB(), "postgresql")


def _uuid() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class Account(Base):
    __tablename__ = "accounts"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    type: Mapped[str] = mapped_column(String(16), default="project")  # school|project|researcher|admin
    name: Mapped[str] = mapped_column(String(200))
    region_coarse: Mapped[str | None] = mapped_column(String(200))
    contact_email: Mapped[str | None] = mapped_column(String(200))
    credit_quota: Mapped[float] = mapped_column(Float, default=0.0)
    credits_used: Mapped[float] = mapped_column(Float, default=0.0)
    email: Mapped[str | None] = mapped_column(String(200), unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(300))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Generation counters per Tripo mode. Incremented with a conditional UPDATE (atomic).
    generations_used_mock: Mapped[int] = mapped_column(Integer, default=0)
    generations_used_live: Mapped[int] = mapped_column(Integer, default=0)
    # Per-account override of the default limit (None = use settings)
    generation_limit: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Invite(Base):
    """Registration invite. Only an HMAC of the code is stored (keyed with SECRET_KEY), so a
    database leak does not reveal usable codes. Codes are created with scripts/invites.py."""

    __tablename__ = "invites"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    code_hash: Mapped[str] = mapped_column(String(64), unique=True)
    note: Mapped[str | None] = mapped_column(String(200))  # e.g. school name
    max_uses: Mapped[int] = mapped_column(Integer, default=1)
    uses: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)  # sha256 of the cookie
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Upload(Base):
    __tablename__ = "uploads"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    key: Mapped[str] = mapped_column(String(300))
    filename: Mapped[str] = mapped_column(String(300))
    content_type: Mapped[str] = mapped_column(String(100))
    size: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Design(Base):
    __tablename__ = "designs"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    code: Mapped[str | None] = mapped_column(String(16), unique=True)  # BT-D-XXXXXX at export
    slug: Mapped[str | None] = mapped_column(String(200))
    title: Mapped[str] = mapped_column(String(200))
    title_en: Mapped[str | None] = mapped_column(String(200))  # English title when `title` is German
    description: Mapped[str | None] = mapped_column(Text)
    description_en: Mapped[str | None] = mapped_column(Text)
    author_account_id: Mapped[str | None] = mapped_column(ForeignKey("accounts.id"))
    parent_design_id: Mapped[str | None] = mapped_column(ForeignKey("designs.id"))
    is_original: Mapped[bool] = mapped_column(Boolean, default=True)
    source_type: Mapped[str] = mapped_column(String(16))  # photo|text|procedural|hybrid
    capture_method: Mapped[str | None] = mapped_column(String(32))
    surface_type: Mapped[str | None] = mapped_column(String(64))
    source_upload_id: Mapped[str | None] = mapped_column(ForeignKey("uploads.id"))
    source_photo_key: Mapped[str | None] = mapped_column(String(300))
    source_prompt: Mapped[str | None] = mapped_column(Text)
    source_negative_prompt: Mapped[str | None] = mapped_column(Text)
    tripo_model_version: Mapped[str | None] = mapped_column(String(64))
    tripo_texture_version: Mapped[str | None] = mapped_column(String(64))
    model_seed: Mapped[int | None] = mapped_column(Integer)
    texture_seed: Mapped[int | None] = mapped_column(Integer)
    image_seed: Mapped[int | None] = mapped_column(Integer)
    raster_seed: Mapped[int] = mapped_column(Integer, default=0)
    enable_image_autofix: Mapped[bool] = mapped_column(Boolean, default=False)
    pipeline_version: Mapped[str | None] = mapped_column(String(16))
    pipeline_params: Mapped[dict] = mapped_column(JSONType, default=dict)
    functional_template: Mapped[str | None] = mapped_column(String(32))
    edge_mode: Mapped[str | None] = mapped_column(String(16))
    texture_period_mm: Mapped[float | None] = mapped_column(Float)
    orientation_mode: Mapped[str | None] = mapped_column(String(32))
    interface_version: Mapped[str | None] = mapped_column(String(8))
    metrics: Mapped[dict] = mapped_column(JSONType, default=dict)
    checks: Mapped[list] = mapped_column(JSONType, default=list)
    files: Mapped[dict] = mapped_column(JSONType, default=dict)
    raw_raster_key: Mapped[str | None] = mapped_column(String(300))
    simulated: Mapped[bool] = mapped_column(Boolean, default=False)  # 3D from the mock fixtures
    heightfield_sha256: Mapped[str | None] = mapped_column(String(64))
    license: Mapped[str] = mapped_column(String(32), default="CC-BY-SA-4.0")
    status: Mapped[str] = mapped_column(String(16), default="draft")  # draft|published|hidden
    stage: Mapped[str] = mapped_column(String(16), default="new")  # new|generating|ready|exported|failed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    tripo_jobs: Mapped[list["TripoJob"]] = relationship(back_populates="design")
    instances: Mapped[list["Instance"]] = relationship(back_populates="design")


class TripoJob(Base):
    __tablename__ = "tripo_jobs"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    design_id: Mapped[str] = mapped_column(ForeignKey("designs.id"))
    kind: Mapped[str] = mapped_column(String(32))
    request: Mapped[dict] = mapped_column(JSONType, default=dict)  # never contains the key
    task_id: Mapped[str | None] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(16), default="queued")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    credits_consumed: Mapped[float | None] = mapped_column(Float)
    error_code: Mapped[int | None] = mapped_column(Integer)
    raw_response: Mapped[dict] = mapped_column(JSONType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    design: Mapped[Design] = relationship(back_populates="tripo_jobs")


class Job(Base):
    """Pipeline job (generate / export) as seen by the UI."""

    __tablename__ = "jobs"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    design_id: Mapped[str] = mapped_column(ForeignKey("designs.id"))
    kind: Mapped[str] = mapped_column(String(16))  # generate|export
    account_id: Mapped[str | None] = mapped_column(ForeignKey("accounts.id"))
    tripo_mode: Mapped[str | None] = mapped_column(String(8))
    counted: Mapped[bool] = mapped_column(Boolean, default=False)  # charged to the quota
    status: Mapped[str] = mapped_column(String(16), default="queued")  # queued|running|success|failed
    progress: Mapped[int] = mapped_column(Integer, default=0)
    step: Mapped[str | None] = mapped_column(String(64))
    error: Mapped[str | None] = mapped_column(Text)
    error_key: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now,
                                                 onupdate=_now)


class Wall(Base):
    __tablename__ = "walls"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    account_id: Mapped[str | None] = mapped_column(ForeignKey("accounts.id"))
    wall_type: Mapped[str] = mapped_column(String(16), default="versuch")
    location_coarse: Mapped[str | None] = mapped_column(String(200))
    orientation_deg: Mapped[float | None] = mapped_column(Float)
    inclination_deg: Mapped[float | None] = mapped_column(Float)
    gap_horizontal_mm: Mapped[float | None] = mapped_column(Float)
    gap_vertical_mm: Mapped[float | None] = mapped_column(Float)
    has_ref_flat: Mapped[bool] = mapped_column(Boolean, default=False)
    has_ref_geo: Mapped[bool] = mapped_column(Boolean, default=False)
    irrigated: Mapped[bool] = mapped_column(Boolean, default=False)
    photo_key: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Instance(Base):
    __tablename__ = "instances"
    id: Mapped[str] = mapped_column(String(20), primary_key=True)  # BT-XXXXXX-NNN
    design_id: Mapped[str] = mapped_column(ForeignKey("designs.id"))
    account_id: Mapped[str | None] = mapped_column(ForeignKey("accounts.id"))
    wall_id: Mapped[str | None] = mapped_column(ForeignKey("walls.id"))
    position_row: Mapped[int | None] = mapped_column(Integer)
    position_col: Mapped[int | None] = mapped_column(Integer)
    format: Mapped[str] = mapped_column(String(4), default="1x1")
    material: Mapped[str] = mapped_column(String(16))
    material_details: Mapped[dict] = mapped_column(JSONType, default=dict)
    process: Mapped[str] = mapped_column(String(16))
    stage: Mapped[int] = mapped_column(Integer, default=1)
    tool_material: Mapped[str | None] = mapped_column(String(16))
    release_agent: Mapped[str | None] = mapped_column(String(64))
    retarder_washed: Mapped[bool] = mapped_column(Boolean, default=False)
    back_type: Mapped[str | None] = mapped_column(String(8))
    channels: Mapped[str] = mapped_column(String(16), default="none")
    booster: Mapped[bool] = mapped_column(Boolean, default=False)
    booster_recipe: Mapped[str | None] = mapped_column(String(1000))  # how it was made (free text)
    booster_source_coarse: Mapped[str | None] = mapped_column(String(200))
    booster_date: Mapped[str | None] = mapped_column(String(10))
    mounting_adapter: Mapped[str | None] = mapped_column(String(16))  # wall|fence|facade|post|tree|other
    mounting_detail: Mapped[str | None] = mapped_column(String(200))  # free text
    cast_date: Mapped[str | None] = mapped_column(String(10))
    installed_date: Mapped[str | None] = mapped_column(String(10))
    orientation_deg: Mapped[float] = mapped_column(Float)  # mandatory
    inclination_deg: Mapped[float | None] = mapped_column(Float)
    height_above_ground_m: Mapped[float | None] = mapped_column(Float)
    shading: Mapped[str | None] = mapped_column(String(16))
    substrate: Mapped[str | None] = mapped_column(String(100))
    location_coarse: Mapped[str | None] = mapped_column(String(200))
    # Optional exact position. Public output is rounded unless geo_visibility == "exact"
    # (never for school accounts).
    geo_lat: Mapped[float | None] = mapped_column(Float)
    geo_lon: Mapped[float | None] = mapped_column(Float)
    geo_visibility: Mapped[str] = mapped_column(String(8), default="approx")  # hidden|approx|exact
    photo_installed_key: Mapped[str | None] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(16), default="active")
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    design: Mapped[Design] = relationship(back_populates="instances")
    observations: Mapped[list["Observation"]] = relationship(back_populates="instance",
                                                             order_by="Observation.observed_at")


class Observation(Base):
    __tablename__ = "observations"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    instance_id: Mapped[str] = mapped_column(ForeignKey("instances.id"))
    observed_at: Mapped[str] = mapped_column(String(10))
    photo_key: Mapped[str | None] = mapped_column(String(300))
    card_detected: Mapped[bool | None] = mapped_column(Boolean)
    green_fraction: Mapped[float | None] = mapped_column(Float)
    dark_fraction: Mapped[float | None] = mapped_column(Float)
    color_metrics: Mapped[dict] = mapped_column(JSONType, default=dict)
    weight_g: Mapped[float | None] = mapped_column(Float)
    species: Mapped[list] = mapped_column(JSONType, default=list)
    notes: Mapped[str | None] = mapped_column(Text)
    observer_role: Mapped[str] = mapped_column(String(16), default="teacher")
    moderation_status: Mapped[str] = mapped_column(String(16), default="approved")  # MVP: no moderation
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    instance: Mapped[Instance] = relationship(back_populates="observations")


_engine = None
_Session = None


def get_engine():
    global _engine, _Session
    if _engine is None:
        from .settings import get_settings

        url = get_settings().database_url
        kwargs = {}
        if url.startswith("sqlite"):
            from pathlib import Path

            Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
            kwargs["connect_args"] = {"check_same_thread": False}
        _engine = create_engine(url, **kwargs)
        _Session = sessionmaker(_engine, expire_on_commit=False)
    return _engine


def SessionLocal():
    get_engine()
    return _Session()


def reset_engine() -> None:
    global _engine, _Session
    _engine = None
    _Session = None


def init_db() -> None:
    engine = get_engine()
    Base.metadata.create_all(engine)
    _add_missing_columns(engine)


def _add_missing_columns(engine) -> None:
    """Tiny forward-only migration for dev databases: add columns that the models gained.
    (Alembic is on the roadmap; until then this keeps existing data usable.)"""
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if not insp.has_table(table.name):
                continue
            have = {c["name"] for c in insp.get_columns(table.name)}
            for col in table.columns:
                if col.name in have:
                    continue
                ddl = col.type.compile(engine.dialect)
                default = ""
                if col.default is not None and getattr(col.default, "is_scalar", False):
                    v = col.default.arg
                    default = f" DEFAULT {int(v) if isinstance(v, bool) else repr(v)}"
                conn.execute(text(f'ALTER TABLE {table.name} ADD COLUMN {col.name} {ddl}{default}'))
