from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from .db import AuditRecord, ConfigurationState, Entity, ExternalVersion, IdempotencyRecord, OutboxEvent, utcnow
from .errors import DomainError
from .security import AuthContext
from .util import digest, now_iso, uuid4


OWNER = {
    "ClinicalCase": "clinical_case", "Observation": "clinical_case", "ResultReceipt": "clinical_case",
    "Evaluation": "inference", "ActionProposal": "pathways", "WorkflowRun": "pathways",
    "Plan": "planning", "Site": "resources", "ManagedResource": "resources",
    "ProcedureEntry": "knowledge", "ResourceCapability": "resources", "AvailabilitySnapshot": "resources",
    "CostQuote": "resources", "Booking": "resources", "ServiceOrder": "integrations",
    "Source": "knowledge", "KnowledgeRelease": "knowledge", "Concept": "knowledge", "Assertion": "knowledge",
    "ModelManifest": "knowledge", "ProtocolManifest": "knowledge", "EvidenceEstimate": "knowledge",
    "Contribution": "contributions", "ProviderPolicy": "integrations", "Operation": "integrations",
    "TreatmentOption": "treatment", "CarePlan": "treatment", "FollowUpTask": "treatment",
    "ImportReport": "knowledge", "OperationalIncident": "audit",
}


def create_entity(
    session: Session,
    ctx: AuthContext,
    kind: str,
    payload: dict,
    *,
    parent_id: str | None = None,
    status: str | None = None,
    foreign_key: str | None = None,
    entity_id: str | None = None,
    envelope: bool = True,
) -> dict:
    eid = entity_id or uuid4()
    ts = now_iso()
    data = dict(payload)
    if envelope:
        data = {"id": eid, "tenant_id": ctx.tenant_id, "revision": 1, "created_at": ts, "updated_at": ts, **data}
    row = Entity(
        id=eid,
        tenant_id=ctx.tenant_id,
        kind=kind,
        owner=OWNER.get(kind, "integrations"),
        revision=int(data.get("revision", 1)),
        parent_id=parent_id,
        status=status or data.get("status") or data.get("lifecycle"),
        foreign_key=foreign_key,
        data=data,
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    session.add(row)
    session.flush()
    return data


def get_row(session: Session, ctx: AuthContext, kind: str, entity_id: str, *, for_update: bool = False) -> Entity:
    stmt = select(Entity).where(Entity.tenant_id == ctx.tenant_id, Entity.kind == kind, Entity.id == entity_id)
    if for_update:
        stmt = stmt.with_for_update()
    row = session.execute(stmt).scalar_one_or_none()
    if row is None:
        raise DomainError("not_found", 404, "Ressource introuvable.")
    return row


def get_entity(session: Session, ctx: AuthContext, kind: str, entity_id: str, *, for_update: bool = False) -> dict:
    return get_row(session, ctx, kind, entity_id, for_update=for_update).data


def update_row(row: Entity, replacement: dict | None = None, **changes: Any) -> dict:
    data = dict(row.data)
    if replacement is not None:
        envelope = {k: data[k] for k in ("id", "tenant_id", "created_at")}
        data = {**envelope, **replacement}
    data.update(changes)
    row.revision += 1
    data["revision"] = row.revision
    data["updated_at"] = now_iso()
    row.status = data.get("status") or data.get("lifecycle")
    row.updated_at = utcnow()
    row.data = data
    return data


def list_entities(session: Session, ctx: AuthContext, kind: str, *, parent_id: str | None = None, status: str | None = None) -> list[dict]:
    stmt: Select = select(Entity).where(Entity.tenant_id == ctx.tenant_id, Entity.kind == kind)
    if parent_id is not None:
        stmt = stmt.where(Entity.parent_id == parent_id)
    if status is not None:
        stmt = stmt.where(Entity.status == status)
    stmt = stmt.order_by(Entity.created_at.asc(), Entity.id.asc())
    return [row.data for row in session.execute(stmt).scalars().all()]


def expected_revision(if_match: str | None) -> int:
    if not if_match:
        raise DomainError("precondition_required", 428, "If-Match est requis.")
    value = if_match.strip()
    if value.startswith("W/"):
        value = value[2:]
    value = value.strip('"')
    try:
        return int(value)
    except ValueError as exc:
        raise DomainError("precondition_failed", 412, "ETag invalide.") from exc


def enforce_match(row: Entity, if_match: str | None) -> None:
    if row.revision != expected_revision(if_match):
        raise DomainError("precondition_failed", 412, "La révision a changé; relire avant de recommander.")


def require_case_revision(row: Entity, case_revision: int) -> None:
    if row.revision != case_revision:
        raise DomainError("stale_case", 409, "La commande repose sur une révision périmée du cas.")


def emit_event(session: Session, ctx: AuthContext, event_type: str, aggregate_type: str, aggregate_id: str, aggregate_revision: int, correlation_id: str, payload: dict) -> None:
    transport_name = event_type if event_type.startswith("medikristal.") else f"medikristal.{event_type}.v1"
    session.add(OutboxEvent(
        event_id=uuid4(), tenant_id=ctx.tenant_id, event_type=transport_name,
        aggregate_type=aggregate_type, aggregate_id=aggregate_id, aggregate_revision=aggregate_revision,
        correlation_id=correlation_id, payload=payload, payload_digest=digest(payload), occurred_at=utcnow(), delivered=False,
    ))


def audit(session: Session, ctx: AuthContext, action: str, correlation_id: str, *, target_kind: str | None = None, target_id: str | None = None, detail: dict | None = None) -> None:
    session.add(AuditRecord(
        id=uuid4(), tenant_id=ctx.tenant_id, principal_id=ctx.principal_id, action=action,
        target_kind=target_kind, target_id=target_id, correlation_id=correlation_id,
        detail=detail or {}, created_at=utcnow(),
    ))


def idempotent(
    session: Session,
    ctx: AuthContext,
    route: str,
    key: str | None,
    request_body: dict,
    action: Callable[[], tuple[dict, int, str | None]],
) -> tuple[dict, int, str | None]:
    if not key:
        raise DomainError("precondition_required", 428, "Idempotency-Key est requis.")
    request_hash = digest(request_body)
    existing = session.execute(select(IdempotencyRecord).where(
        IdempotencyRecord.tenant_id == ctx.tenant_id,
        IdempotencyRecord.principal_id == ctx.principal_id,
        IdempotencyRecord.route == route,
        IdempotencyRecord.key == key,
    )).scalar_one_or_none()
    if existing:
        if existing.request_hash != request_hash:
            raise DomainError("idempotency_conflict", 409, "Cette clé d'idempotence a déjà été utilisée avec une autre demande.")
        return existing.response_json, existing.status_code, existing.etag
    payload, status_code, etag = action()
    session.add(IdempotencyRecord(
        id=uuid4(), tenant_id=ctx.tenant_id, principal_id=ctx.principal_id, route=route, key=key,
        request_hash=request_hash, status_code=status_code, etag=etag, response_json=payload, created_at=utcnow(),
    ))
    return payload, status_code, etag


def get_configuration(session: Session, ctx: AuthContext, default: dict) -> tuple[dict, int]:
    row = session.get(ConfigurationState, ctx.tenant_id)
    if row is None:
        row = ConfigurationState(tenant_id=ctx.tenant_id, revision=1, data=default, updated_at=utcnow())
        session.add(row)
        session.flush()
    return dict(row.data), row.revision


def register_external_version(session: Session, ctx: AuthContext, namespace: str, foreign_id: str, foreign_version: str, payload: dict, entity_id: str) -> str | None:
    content_digest = digest(payload)
    existing = session.execute(select(ExternalVersion).where(
        ExternalVersion.tenant_id == ctx.tenant_id, ExternalVersion.namespace == namespace,
        ExternalVersion.foreign_id == foreign_id, ExternalVersion.foreign_version == foreign_version,
    )).scalar_one_or_none()
    if existing:
        if existing.digest != content_digest:
            raise DomainError("source_version_conflict", 409, "Même identité/version externe avec contenu divergent.")
        return existing.entity_id
    session.add(ExternalVersion(
        id=uuid4(), tenant_id=ctx.tenant_id, namespace=namespace, foreign_id=foreign_id,
        foreign_version=foreign_version, digest=content_digest, entity_id=entity_id, created_at=utcnow(),
    ))
    return None
