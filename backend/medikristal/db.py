from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterator

from sqlalchemy import Boolean, DateTime, Integer, JSON, LargeBinary, String, UniqueConstraint, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from .config import load_settings


class Base(DeclarativeBase):
    pass


class Entity(Base):
    __tablename__ = "mk_entities"
    __table_args__ = (
        UniqueConstraint("tenant_id", "kind", "id", name="uq_entity_tenant_kind_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), index=True)
    kind: Mapped[str] = mapped_column(String(64), index=True)
    owner: Mapped[str] = mapped_column(String(32), index=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    parent_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    status: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    foreign_key: Mapped[str | None] = mapped_column(String(512), index=True, nullable=True)
    data: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EntityRevision(Base):
    """Append-only snapshots for mutable entities.

    The live row remains convenient for reads, while this table preserves every admitted
    version so corrections/revocations never destroy historical state.
    """

    __tablename__ = "mk_entity_revisions"
    __table_args__ = (
        UniqueConstraint("tenant_id", "kind", "entity_id", "revision", name="uq_entity_revision"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), index=True)
    kind: Mapped[str] = mapped_column(String(64), index=True)
    entity_id: Mapped[str] = mapped_column(String(36), index=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    data: Mapped[dict] = mapped_column(JSON, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CaseAccess(Base):
    """Local case grant independent from operation-level permissions."""

    __tablename__ = "mk_case_access"
    __table_args__ = (
        UniqueConstraint("tenant_id", "case_id", "principal_id", name="uq_case_access"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), index=True)
    case_id: Mapped[str] = mapped_column(String(36), index=True)
    principal_id: Mapped[str] = mapped_column(String(128), index=True)
    grant_kind: Mapped[str] = mapped_column(String(32), nullable=False, default="explicit")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ReservationClaim(Base):
    """Database-enforced claim for a capacity slot.

    A row exists while a booking is active. The unique key turns the last-slot race into
    a database invariant rather than a check-then-insert convention.
    """

    __tablename__ = "mk_reservation_claims"
    __table_args__ = (
        UniqueConstraint("tenant_id", "capability_id", "slot_id", "unit_index", name="uq_reservation_claim"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), index=True)
    capability_id: Mapped[str] = mapped_column(String(36), index=True)
    slot_id: Mapped[str] = mapped_column(String(256), nullable=False)
    unit_index: Mapped[int] = mapped_column(Integer, nullable=False)
    booking_id: Mapped[str] = mapped_column(String(36), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class InboxEvent(Base):
    __tablename__ = "mk_inbox"
    __table_args__ = (
        UniqueConstraint("consumer", "event_id", name="uq_inbox_consumer_event"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    consumer: Mapped[str] = mapped_column(String(128), index=True)
    event_id: Mapped[str] = mapped_column(String(36), index=True)
    payload_digest: Mapped[str] = mapped_column(String(71), nullable=False)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class IdempotencyRecord(Base):
    __tablename__ = "mk_idempotency"
    __table_args__ = (
        UniqueConstraint("tenant_id", "principal_id", "route", "key", name="uq_idempotency_scope"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), index=True)
    principal_id: Mapped[str] = mapped_column(String(128), index=True)
    route: Mapped[str] = mapped_column(String(200), index=True)
    key: Mapped[str] = mapped_column(String(200))
    request_hash: Mapped[str] = mapped_column(String(71), nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    etag: Mapped[str | None] = mapped_column(String(64), nullable=True)
    response_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ExternalVersion(Base):
    __tablename__ = "mk_external_versions"
    __table_args__ = (
        UniqueConstraint("tenant_id", "namespace", "foreign_id", "foreign_version", name="uq_external_version"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), index=True)
    namespace: Mapped[str] = mapped_column(String(120), index=True)
    foreign_id: Mapped[str] = mapped_column(String(256))
    foreign_version: Mapped[str] = mapped_column(String(256))
    digest: Mapped[str] = mapped_column(String(71), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class OutboxEvent(Base):
    __tablename__ = "mk_outbox"

    event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), index=True)
    event_type: Mapped[str] = mapped_column(String(160), index=True)
    aggregate_type: Mapped[str] = mapped_column(String(64))
    aggregate_id: Mapped[str] = mapped_column(String(36), index=True)
    aggregate_revision: Mapped[int] = mapped_column(Integer)
    correlation_id: Mapped[str] = mapped_column(String(36), index=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    payload_digest: Mapped[str] = mapped_column(String(71), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    delivered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class ConfigurationState(Base):
    __tablename__ = "mk_configuration"

    tenant_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    data: Mapped[dict] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AuditRecord(Base):
    __tablename__ = "mk_audit"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), index=True)
    principal_id: Mapped[str] = mapped_column(String(128), index=True)
    action: Mapped[str] = mapped_column(String(160), index=True)
    target_kind: Mapped[str | None] = mapped_column(String(64), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    correlation_id: Mapped[str] = mapped_column(String(36), index=True)
    detail: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Blob(Base):
    __tablename__ = "mk_blobs"
    __table_args__ = (
        UniqueConstraint("tenant_id", "digest", name="uq_blob_digest"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), index=True)
    digest: Mapped[str] = mapped_column(String(71), index=True)
    media_type: Mapped[str] = mapped_column(String(128), nullable=False)
    classification: Mapped[str] = mapped_column(String(64), nullable=False)
    content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


settings = load_settings()
engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False, future=True)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def get_session() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
