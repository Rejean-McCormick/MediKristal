from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, object_session

from .db import (
    AuditRecord,
    CaseAccess,
    ConfigurationState,
    Entity,
    EntityRevision,
    ExternalVersion,
    IdempotencyRecord,
    OutboxEvent,
    utcnow,
)
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
    "ImportReport": "knowledge", "OperationalIncident": "audit", "ImpactAnalysis": "audit",
    "SourceSnapshot": "knowledge", "KnowledgeArtifact": "knowledge", "ImportRun": "knowledge",
    "RawRecord": "knowledge", "MappingCandidate": "knowledge", "ImportIssue": "knowledge",
}

# Entity kinds whose parent_id is always a ClinicalCase id.
DIRECT_CASE_SCOPED = {
    "Observation", "ResultReceipt", "Evaluation", "ActionProposal", "WorkflowRun", "Plan",
    "ServiceOrder", "TreatmentOption", "CarePlan", "FollowUpTask", "Operation",
}


def _snapshot(session: Session, row: Entity) -> None:
    session.add(EntityRevision(
        id=uuid4(), tenant_id=row.tenant_id, kind=row.kind, entity_id=row.id,
        revision=row.revision, data=deepcopy(row.data), recorded_at=utcnow(),
    ))


def grant_case_access(session: Session, ctx: AuthContext, case_id: str, principal_id: str | None = None, grant_kind: str = "explicit") -> None:
    principal = principal_id or ctx.principal_id
    existing = session.execute(select(CaseAccess).where(
        CaseAccess.tenant_id == ctx.tenant_id,
        CaseAccess.case_id == case_id,
        CaseAccess.principal_id == principal,
    )).scalar_one_or_none()
    if existing is None:
        session.add(CaseAccess(
            id=uuid4(), tenant_id=ctx.tenant_id, case_id=case_id, principal_id=principal,
            grant_kind=grant_kind, created_at=utcnow(),
        ))
        session.flush()


def has_case_access(session: Session, ctx: AuthContext, case_id: str) -> bool:
    if "*" in ctx.permissions:
        return True
    grants = getattr(ctx, "case_grants", frozenset())
    if "*" in grants or case_id in grants:
        return True
    return session.execute(select(CaseAccess.id).where(
        CaseAccess.tenant_id == ctx.tenant_id,
        CaseAccess.case_id == case_id,
        CaseAccess.principal_id == ctx.principal_id,
    )).scalar_one_or_none() is not None


def require_case_access(session: Session, ctx: AuthContext, case_id: str) -> None:
    if not has_case_access(session, ctx, case_id):
        # Deliberately indistinguishable from a missing case to avoid an existence oracle.
        raise DomainError("not_found", 404, "Ressource introuvable.")


def accessible_case_ids(session: Session, ctx: AuthContext) -> set[str] | None:
    if "*" in ctx.permissions or "*" in getattr(ctx, "case_grants", frozenset()):
        return None
    result = set(getattr(ctx, "case_grants", frozenset()))
    result.discard("*")
    result.update(session.execute(select(CaseAccess.case_id).where(
        CaseAccess.tenant_id == ctx.tenant_id,
        CaseAccess.principal_id == ctx.principal_id,
    )).scalars().all())
    return result


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
    data = deepcopy(payload)
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
    _snapshot(session, row)
    if kind == "ClinicalCase":
        grant_case_access(session, ctx, eid, ctx.principal_id, "creator")
    return deepcopy(data)


def _scope_row(session: Session, ctx: AuthContext, row: Entity) -> None:
    if row.kind == "ClinicalCase":
        require_case_access(session, ctx, row.id)
    elif row.kind in DIRECT_CASE_SCOPED and row.parent_id:
        require_case_access(session, ctx, row.parent_id)
    elif row.kind == "Booking" and row.parent_id:
        # Booking parent is an order; the order parent is the case.
        order = session.execute(select(Entity).where(
            Entity.tenant_id == ctx.tenant_id, Entity.kind == "ServiceOrder", Entity.id == row.parent_id,
        )).scalar_one_or_none()
        if order is not None and order.parent_id:
            require_case_access(session, ctx, order.parent_id)


def get_row(session: Session, ctx: AuthContext, kind: str, entity_id: str, *, for_update: bool = False) -> Entity:
    stmt = select(Entity).where(Entity.tenant_id == ctx.tenant_id, Entity.kind == kind, Entity.id == entity_id)
    if for_update:
        stmt = stmt.with_for_update()
    row = session.execute(stmt).scalar_one_or_none()
    if row is None:
        raise DomainError("not_found", 404, "Ressource introuvable.")
    _scope_row(session, ctx, row)
    return row


def get_entity(session: Session, ctx: AuthContext, kind: str, entity_id: str, *, for_update: bool = False) -> dict:
    return deepcopy(get_row(session, ctx, kind, entity_id, for_update=for_update).data)


def update_row(row: Entity, replacement: dict | None = None, **changes: Any) -> dict:
    session = object_session(row)
    if session is None:
        raise RuntimeError("Entity row is detached from its session")
    data = deepcopy(row.data)
    enveloped = all(k in data for k in ("id", "tenant_id", "revision", "created_at", "updated_at"))
    if replacement is not None:
        if enveloped:
            envelope = {k: data[k] for k in ("id", "tenant_id", "created_at")}
            data = {**envelope, **deepcopy(replacement)}
        else:
            data = deepcopy(replacement)
    data.update(deepcopy(changes))
    row.revision += 1
    if enveloped:
        data["revision"] = row.revision
        data["updated_at"] = now_iso()
    row.status = data.get("status") or data.get("lifecycle")
    row.updated_at = utcnow()
    row.data = data
    session.flush()
    _snapshot(session, row)
    return deepcopy(data)


def list_entities(session: Session, ctx: AuthContext, kind: str, *, parent_id: str | None = None, status: str | None = None) -> list[dict]:
    stmt: Select = select(Entity).where(Entity.tenant_id == ctx.tenant_id, Entity.kind == kind)
    if parent_id is not None:
        if kind in DIRECT_CASE_SCOPED:
            require_case_access(session, ctx, parent_id)
        stmt = stmt.where(Entity.parent_id == parent_id)
    elif kind == "ClinicalCase":
        ids = accessible_case_ids(session, ctx)
        if ids is not None:
            if not ids:
                return []
            stmt = stmt.where(Entity.id.in_(ids))
    elif kind in DIRECT_CASE_SCOPED:
        ids = accessible_case_ids(session, ctx)
        if ids is not None:
            if not ids:
                return []
            stmt = stmt.where(Entity.parent_id.in_(ids))
    if status is not None:
        stmt = stmt.where(Entity.status == status)
    stmt = stmt.order_by(Entity.created_at.asc(), Entity.id.asc())
    return [deepcopy(row.data) for row in session.execute(stmt).scalars().all()]


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
        correlation_id=correlation_id, payload=deepcopy(payload), payload_digest=digest(payload), occurred_at=utcnow(), delivered=False,
    ))


def audit(session: Session, ctx: AuthContext, action: str, correlation_id: str, *, target_kind: str | None = None, target_id: str | None = None, detail: dict | None = None) -> None:
    session.add(AuditRecord(
        id=uuid4(), tenant_id=ctx.tenant_id, principal_id=ctx.principal_id, action=action,
        target_kind=target_kind, target_id=target_id, correlation_id=correlation_id,
        detail=deepcopy(detail or {}), created_at=utcnow(),
    ))


def idempotent(
    session: Session,
    ctx: AuthContext,
    route: str,
    key: str | None,
    request_body: dict,
    action: Callable[[], tuple[dict, int, str | None]],
) -> tuple[dict, int, str | None]:
    """Run a command once per tenant/principal/route/key.

    The key claim is flushed before domain mutation. The database unique constraint is the
    concurrency authority, so concurrent requests cannot both enter ``action``. A command
    failure explicitly rolls the transaction back because handled HTTP domain errors do not
    reliably propagate into framework dependency finalizers on every supported stack.
    """
    if not key:
        raise DomainError("precondition_required", 428, "Idempotency-Key est requis.")
    request_hash = digest(request_body)

    def find_existing() -> IdempotencyRecord | None:
        return session.execute(select(IdempotencyRecord).where(
            IdempotencyRecord.tenant_id == ctx.tenant_id,
            IdempotencyRecord.principal_id == ctx.principal_id,
            IdempotencyRecord.route == route,
            IdempotencyRecord.key == key,
        )).scalar_one_or_none()

    existing = find_existing()
    if existing is not None:
        if existing.request_hash != request_hash:
            raise DomainError("idempotency_conflict", 409, "Cette clé d'idempotence a déjà été utilisée avec une autre demande.")
        return deepcopy(existing.response_json), existing.status_code, existing.etag

    marker = IdempotencyRecord(
        id=uuid4(), tenant_id=ctx.tenant_id, principal_id=ctx.principal_id, route=route, key=key,
        request_hash=request_hash, status_code=102, etag=None, response_json={"pending": True}, created_at=utcnow(),
    )
    try:
        session.add(marker)
        session.flush()
    except IntegrityError:
        # No domain mutation has occurred yet. Reset the failed transaction, then return the
        # winner's durable response (or a retryable conflict if it is still unavailable).
        session.rollback()
        existing = find_existing()
        if existing is None:
            raise DomainError("idempotency_conflict", 409, "La clé d'idempotence est déjà en cours de traitement.", retryable=True)
        if existing.request_hash != request_hash:
            raise DomainError("idempotency_conflict", 409, "Cette clé d'idempotence a déjà été utilisée avec une autre demande.")
        return deepcopy(existing.response_json), existing.status_code, existing.etag

    try:
        payload, status_code, etag = action()
        marker.status_code = status_code
        marker.etag = etag
        marker.response_json = deepcopy(payload)
        session.flush()
        return payload, status_code, etag
    except Exception:
        # Undo the key claim and every mutation the failed command may have performed.
        session.rollback()
        raise


def get_configuration(session: Session, ctx: AuthContext, default: dict) -> tuple[dict, int]:
    row = session.get(ConfigurationState, ctx.tenant_id)
    if row is None:
        row = ConfigurationState(tenant_id=ctx.tenant_id, revision=1, data=deepcopy(default), updated_at=utcnow())
        session.add(row)
        session.flush()
    return deepcopy(row.data), row.revision


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
