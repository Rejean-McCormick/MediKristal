from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from fastapi import APIRouter, Body, Depends, Header, Query, Request
from fastapi.responses import ORJSONResponse
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import synthetic as syn
from .adapters import facility_adapter
from .config import load_settings
from .contracts import validate
from .db import ConfigurationState, Entity, ExternalVersion, ReservationClaim, get_session, utcnow
from .errors import DomainError
from .importers import MAPPING_VERSION, PARSER_VERSION, existing_source_snapshot, parse_local_catalog_csv, resolve_blob
from .security import AuthContext, auth_context, authorize
from .store import (
    DIRECT_CASE_SCOPED,
    audit,
    create_entity,
    emit_event,
    enforce_match,
    expected_revision,
    get_configuration,
    get_entity,
    get_row,
    idempotent,
    list_entities,
    register_external_version,
    require_case_revision,
    update_row,
)
from .util import artifact_ref, digest, now_iso, uuid4

settings = load_settings()
router = APIRouter(prefix="/api/v1")


def _cursor_secret() -> bytes:
    # Production startup already rejects a missing/short auth secret. The development
    # fallback merely keeps the reference runtime usable without pretending to provide
    # production-grade secret management.
    return (settings.auth_secret or "medikristal-development-cursor-key").encode()


def _b64_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def _b64_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _cursor_scope(scope: dict[str, Any] | None) -> str:
    return digest(scope or {})


def _encode_cursor(ctx: AuthContext, route: str, offset: int, scope: dict[str, Any] | None) -> str:
    payload = {
        "v": 1,
        "tenant": ctx.tenant_id,
        "principal": ctx.principal_id,
        "route": route,
        "scope": _cursor_scope(scope),
        "offset": offset,
    }
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    signature = hmac.new(_cursor_secret(), body, hashlib.sha256).digest()
    return f"{_b64_encode(body)}.{_b64_encode(signature)}"


def _decode_cursor(ctx: AuthContext, route: str, cursor: str, scope: dict[str, Any] | None) -> int:
    try:
        body_b64, signature_b64 = cursor.split(".", 1)
        body = _b64_decode(body_b64)
        signature = _b64_decode(signature_b64)
        expected = hmac.new(_cursor_secret(), body, hashlib.sha256).digest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError("signature")
        payload = json.loads(body)
        if payload != {
            "v": 1,
            "tenant": ctx.tenant_id,
            "principal": ctx.principal_id,
            "route": route,
            "scope": _cursor_scope(scope),
            "offset": payload.get("offset"),
        }:
            raise ValueError("scope")
        offset = payload["offset"]
        if not isinstance(offset, int) or isinstance(offset, bool) or offset < 0:
            raise ValueError("offset")
        return offset
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise DomainError("invalid_request", 422, "Curseur de pagination invalide ou hors contexte.") from exc


def page(
    items: list[dict],
    *,
    ctx: AuthContext,
    route: str,
    cursor: str | None = None,
    limit: int = 50,
    scope: dict[str, Any] | None = None,
) -> dict:
    offset = _decode_cursor(ctx, route, cursor, scope) if cursor else 0
    selected = items[offset:offset + limit]
    next_offset = offset + len(selected)
    next_cursor = _encode_cursor(ctx, route, next_offset, scope) if next_offset < len(items) else None
    return {"items": selected, "next_cursor": next_cursor}


def response(payload: dict, status_code: int = 200, etag: str | None = None) -> ORJSONResponse:
    headers = {"ETag": f'"{etag}"'} if etag is not None else None
    return ORJSONResponse(payload, status_code=status_code, headers=headers)


def op(ctx: AuthContext, operation_id: str) -> None:
    authorize(ctx, operation_id)


def correlation(request: Request) -> str:
    return request.state.correlation_id


def _ts(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DomainError("invalid_request", 422, "Horodatage invalide.") from exc
    if parsed.tzinfo is None:
        raise DomainError("invalid_request", 422, "Un fuseau horaire explicite est requis.")
    return parsed.astimezone(timezone.utc)


def _same_artifact_ref(a: dict, b: dict) -> bool:
    return all(a.get(k) == b.get(k) for k in ("id", "version", "digest"))


def _require_known_ref(ref: dict, candidates: list[dict], label: str) -> dict:
    item = next((candidate for candidate in candidates if _same_artifact_ref(ref, candidate)), None)
    if item is None:
        same_id = next((candidate for candidate in candidates if candidate.get("id") == ref.get("id")), None)
        if same_id is not None:
            raise DomainError("artifact_integrity_failed", 422, f"Digest ou version invalide pour {label}.")
        raise DomainError("not_found", 404, f"{label.capitalize()} introuvable.")
    return item


def _release_row_by_digest(db: Session, ctx: AuthContext, release_digest: str) -> Entity | None:
    return db.execute(select(Entity).where(
        Entity.tenant_id == ctx.tenant_id, Entity.kind == "KnowledgeRelease", Entity.foreign_key == release_digest
    )).scalars().first()


def _release_row_by_selector(db: Session, ctx: AuthContext, selector: str) -> Entity | None:
    return db.execute(select(Entity).where(
        Entity.tenant_id == ctx.tenant_id, Entity.kind == "KnowledgeRelease",
        (Entity.id == selector) | (Entity.foreign_key == selector),
    )).scalars().first()


def _release_refs(db: Session, ctx: AuthContext, selector: str | None, field: str) -> set[tuple[str, str, str]] | None:
    if selector is None:
        return None
    if selector in {syn.SYN_RELEASE["id"], syn.SYN_RELEASE["digest"]}:
        candidates = syn.models() if field == "model_refs" else syn.protocols()
        return {(x["id"], x["version"], x["digest"]) for x in candidates}
    row = _release_row_by_selector(db, ctx, selector)
    if row is None or row.data.get("status") == "revoked":
        return set()
    return {(x["id"], x["version"], x["digest"]) for x in row.data.get(field, [])}


def _require_engineering_policy(ref: dict) -> None:
    if not _same_artifact_ref(ref, syn.AUTH_POLICY):
        same_id = ref.get("id") == syn.AUTH_POLICY["id"]
        code = "artifact_integrity_failed" if same_id else "release_not_admitted"
        status = 422 if same_id else 409
        raise DomainError(code, status, "La politique d'admission engineering fournie n'est pas reconnue.")


def _require_evaluation_artifacts(db: Session, ctx: AuthContext, body: dict) -> None:
    # The bundled synthetic release is a built-in immutable engineering fixture. Other
    # releases must have been built, published and not revoked in this tenant.
    if not _same_artifact_ref(body["knowledge_release"], syn.SYN_RELEASE):
        release = _release_row_by_digest(db, ctx, body["knowledge_release"]["digest"])
        if release is None:
            raise DomainError("not_found", 404, "Release de connaissances introuvable.")
        data = release.data
        if data.get("release_id") != body["knowledge_release"]["digest"] or data.get("version") != body["knowledge_release"]["version"]:
            raise DomainError("artifact_integrity_failed", 422, "La référence de release ne correspond pas au manifeste stocké.")
        if data.get("status") != "published":
            raise DomainError("release_not_admitted", 409, "La release n'est pas publiée ou a été révoquée.")
    for model_ref in body["model_refs"]:
        _require_known_ref(model_ref, syn.models(), "modèle")


def _concept_key(concept: dict) -> tuple[str, str, str]:
    return (concept.get("system", ""), concept.get("code", ""), concept.get("version", ""))


def _validate_procedure_graph(db: Session, ctx: AuthContext, candidate: dict, replacing_id: str | None = None) -> None:
    entries = list_entities(db, ctx, "ProcedureEntry")
    graph: dict[tuple[str, str, str], set[tuple[str, str, str]]] = {}
    for entry in entries:
        if replacing_id and entry["id"] == replacing_id:
            continue
        graph[_concept_key(entry["concept"])] = {_concept_key(c) for c in entry.get("component_refs", [])}
    key = _concept_key(candidate["concept"])
    graph[key] = {_concept_key(c) for c in candidate.get("component_refs", [])}
    if key in graph[key]:
        raise DomainError("invalid_request", 422, "Un acte ne peut pas se contenir lui-même comme composant.")

    visiting: set[tuple[str, str, str]] = set()
    visited: set[tuple[str, str, str]] = set()

    def visit(node: tuple[str, str, str]) -> None:
        if node in visiting:
            raise DomainError("catalog_reference_in_use", 409, "Cycle détecté dans la composition du catalogue d'actes.")
        if node in visited:
            return
        visiting.add(node)
        for child in graph.get(node, set()):
            if child in graph:
                visit(child)
        visiting.remove(node)
        visited.add(node)

    for node in list(graph):
        visit(node)


def _record_resource_impacts(db: Session, ctx: AuthContext, resource: Entity, corr: str, reason: str) -> list[str]:
    impacted: list[str] = []
    aliases = {resource.id, str(resource.data.get("external_id", ""))}
    capabilities = db.execute(select(Entity).where(
        Entity.tenant_id == ctx.tenant_id, Entity.kind == "ResourceCapability"
    )).scalars().all()
    cap_ids = {c.id for c in capabilities if aliases.intersection(set(c.data.get("resource_refs", [])))}
    if not cap_ids:
        return impacted
    bookings = db.execute(select(Entity).where(
        Entity.tenant_id == ctx.tenant_id, Entity.kind == "Booking",
        Entity.status.in_(["held", "confirm_requested", "confirmed", "reconciling"]),
    )).scalars().all()
    for booking in bookings:
        if booking.data.get("capability_id") not in cap_ids:
            continue
        impact = create_entity(db, ctx, "ImpactAnalysis", {
            "subject_kind": "Booking", "subject_id": booking.id, "source_kind": "ManagedResource",
            "source_id": resource.id, "reason": reason, "status": "open", "created_by_event": "catalog.changed",
        }, status="open")
        operation = make_operation(db, ctx, "replan_booking", booking.id, corr, status="queued")
        emit_event(db, ctx, "booking.replan_requested", "Booking", booking.id, booking.revision, corr, {
            "booking_id": booking.id, "impact_id": impact["id"], "operation_id": operation["id"], "reason": reason,
        })
        impacted.append(booking.id)
    return impacted


def _find_catalog_entity(db: Session, ctx: AuthContext, kind: str, ref: str) -> Entity:
    row = db.execute(select(Entity).where(
        Entity.tenant_id == ctx.tenant_id, Entity.kind == kind,
        (Entity.id == ref) | (Entity.data["external_id"].as_string() == ref),
    )).scalars().first()
    if row is None:
        raise DomainError("not_found", 404, f"Référence {kind} introuvable.")
    return row


def _validate_capability_refs(db: Session, ctx: AuthContext, payload: dict) -> None:
    site = _find_catalog_entity(db, ctx, "Site", payload["site_ref"])
    if site.data.get("status") != "active":
        raise DomainError("catalog_reference_in_use", 409, "La capacité exige un site actif.")
    for resource_ref in payload.get("resource_refs", []):
        resource = _find_catalog_entity(db, ctx, "ManagedResource", resource_ref)
        if resource.data.get("status") != "active":
            raise DomainError("catalog_reference_in_use", 409, "Une ressource indisponible ou retirée ne peut soutenir une nouvelle capacité.")
        if resource.data.get("site_id") != site.id:
            raise DomainError("authorization_scope_mismatch", 403, "La ressource et le site de la capacité ne correspondent pas.")
    if payload["procedure"].get("system") != syn.SYN:
        key = _concept_key(payload["procedure"])
        entry = next((x for x in list_entities(db, ctx, "ProcedureEntry") if _concept_key(x["concept"]) == key and x.get("status") == "active"), None)
        if entry is None:
            raise DomainError("not_found", 404, "Acte actif absent du catalogue de procédures.")


def _release_ref_for_row(row: Entity) -> dict:
    return {"id": row.data["release_id"], "version": row.data["version"], "digest": row.data["release_id"]}


def stale_case_dependents(db: Session, ctx: AuthContext, case_id: str, new_revision: int) -> None:
    for kind in ("Evaluation", "ActionProposal", "Plan", "TreatmentOption"):
        for row in db.execute(select(Entity).where(Entity.tenant_id == ctx.tenant_id, Entity.kind == kind, Entity.parent_id == case_id)).scalars().all():
            data = dict(row.data)
            if int(data.get("case_revision", 0)) < new_revision:
                if kind == "Evaluation" and not data.get("stale", False):
                    update_row(row, stale=True)
                elif kind == "ActionProposal" and data.get("status") in {"proposed", "accepted"}:
                    update_row(row, status="superseded")
                elif kind == "TreatmentOption" and data.get("status") in {"proposed", "needs_information"}:
                    update_row(row, status="superseded")


def make_operation(db: Session, ctx: AuthContext, kind: str, result_ref: str | None, corr: str, status: str = "succeeded", error_code: str | None = None) -> dict:
    case_parent: str | None = None
    if result_ref:
        result = db.execute(select(Entity).where(
            Entity.tenant_id == ctx.tenant_id, Entity.id == result_ref,
        )).scalars().first()
        if result is not None:
            if result.kind in DIRECT_CASE_SCOPED - {"Operation"} and result.parent_id:
                case_parent = result.parent_id
            elif result.kind == "Booking" and result.parent_id:
                order = db.execute(select(Entity).where(
                    Entity.tenant_id == ctx.tenant_id, Entity.kind == "ServiceOrder", Entity.id == result.parent_id,
                )).scalars().first()
                case_parent = order.parent_id if order is not None else None
    return create_entity(db, ctx, "Operation", {
        "kind": kind, "status": status, "result_ref": result_ref, "error_code": error_code, "correlation_id": corr,
    }, parent_id=case_parent, status=status)


def catalog_create(kind: str, schema: str, payload: dict, db: Session, ctx: AuthContext) -> dict:
    validate(schema, payload)
    if kind == "ProcedureEntry":
        _validate_procedure_graph(db, ctx, payload)
        key = _concept_key(payload["concept"])
        duplicate = next((x for x in list_entities(db, ctx, "ProcedureEntry") if _concept_key(x["concept"]) == key), None)
        if duplicate:
            raise DomainError("source_version_conflict", 409, "Ce concept d'acte existe déjà dans le catalogue local.")
    if kind == "ManagedResource":
        site = get_row(db, ctx, "Site", payload["site_id"])
        if site.data.get("status") != "active" and payload.get("status") == "active":
            raise DomainError("catalog_reference_in_use", 409, "Une ressource active exige un site actif.")
        duplicate = next((x for x in list_entities(db, ctx, "ManagedResource") if x["site_id"] == payload["site_id"] and x["external_id"] == payload["external_id"]), None)
        if duplicate:
            raise DomainError("source_version_conflict", 409, "Cet identifiant de ressource existe déjà sur ce site.")
    if kind == "Site":
        duplicate = next((x for x in list_entities(db, ctx, "Site") if x["owner"] == payload["owner"] and x["external_id"] == payload["external_id"]), None)
        if duplicate:
            raise DomainError("source_version_conflict", 409, "Cet identifiant de site existe déjà pour ce propriétaire.")
    parent_id = payload.get("site_id") if kind == "ManagedResource" else None
    return create_entity(db, ctx, kind, payload, parent_id=parent_id, status=payload.get("status"))


def catalog_revise(kind: str, schema: str, item_id: str, body: dict, if_match: str | None, db: Session, ctx: AuthContext) -> dict:
    validate(schema, body)
    row = get_row(db, ctx, kind, item_id, for_update=True)
    enforce_match(row, if_match)
    replacement = body["replacement"]
    if kind == "ProcedureEntry":
        _validate_procedure_graph(db, ctx, replacement, replacing_id=item_id)
        if replacement.get("status") == "retired" and row.data.get("status") != "retired":
            current_key = _concept_key(row.data["concept"])
            for entry in list_entities(db, ctx, "ProcedureEntry"):
                if entry["id"] != item_id and entry.get("status") == "active" and current_key in {_concept_key(c) for c in entry.get("component_refs", [])}:
                    raise DomainError("catalog_reference_in_use", 409, "L'acte est encore référencé comme composant d'un acte actif.")
    if kind == "ManagedResource":
        site = get_row(db, ctx, "Site", replacement["site_id"])
        if site.data.get("status") != "active" and replacement.get("status") == "active":
            raise DomainError("catalog_reference_in_use", 409, "Une ressource active exige un site actif.")
    updated = update_row(row, replacement=replacement)
    row.parent_id = replacement.get("site_id") if kind == "ManagedResource" else row.parent_id
    return updated


@router.get("/capabilities")
def get_capabilities(request: Request, db: Session = Depends(get_session), ctx: AuthContext = Depends(auth_context)):
    op(ctx, "getCapabilities")
    cfg, _ = get_configuration(db, ctx, settings.configuration_default)
    network = cfg["network_scope"]
    provider_state = "unavailable"
    if network == "internet" and cfg["mode"] == "online_extended":
        provider_state = "not_configured"
        now = datetime.now(timezone.utc)
        latest: dict[str, dict] = {}
        for policy in list_entities(db, ctx, "ProviderPolicy"):
            latest[policy["provider_id"]] = policy
        for provider_id in cfg.get("provider_allowlist", []):
            policy = latest.get(provider_id)
            if not policy:
                continue
            if (policy.get("enabled") and cfg["mode"] in policy.get("allowed_modes", [])
                    and policy.get("currency") == cfg.get("currency")
                    and _ts(policy["period_start"]) <= now < _ts(policy["period_end"])
                    and int(cfg.get("paid_budget_minor", 0)) > 0
                    and int(policy.get("budget_minor", 0)) > 0):
                provider_state = "available"
                break
    core = [
        ("cases", "available", False, False), ("observations", "available", False, False),
        ("synthetic_inference", "available", False, False), ("workflows", "available", False, False),
        ("planning", "available", False, False), ("resources", "available", False, False),
        ("treatment_options", "available", False, False), ("followup", "available", False, False),
        ("knowledge_registry", "available", False, False), ("contributions", "available", False, False),
        ("provider_network", provider_state, True, True),
        ("fhir_partner", "not_configured", True, False), ("kristal_export", "not_configured", False, False),
    ]
    caps = [{"name": n, "state": s, "requires_network": rn, "paid": p, "supported_uses": ["engineering"], "limitations": (["Données et modèles cliniques réels non livrés."] if n != "provider_network" else ["Aucun fournisseur activé implicitement."])} for n, s, rn, p in core]
    payload = {"api_version": "0.2.0", "mode": cfg["mode"], "network_scope": cfg["network_scope"], "capabilities": caps}
    validate("Capabilities", payload)
    return payload


@router.post("/cases")
def create_case(request: Request, body: dict = Body(...), idempotency_key: str | None = Header(None, alias="Idempotency-Key"), db: Session = Depends(get_session), ctx: AuthContext = Depends(auth_context)):
    op(ctx, "createCase"); validate("CreateCase", body)
    def action():
        case = create_entity(db, ctx, "ClinicalCase", {**body, "lifecycle": "draft"}, status="draft")
        audit(db, ctx, "case.created", correlation(request), target_kind="ClinicalCase", target_id=case["id"])
        emit_event(db, ctx, "case.created", "ClinicalCase", case["id"], case["revision"], correlation(request), {"case_id": case["id"]})
        return case, 201, str(case["revision"])
    payload, status, etag = idempotent(db, ctx, "createCase", idempotency_key, body, action)
    return response(payload, status, etag)


@router.get("/cases")
def list_cases(cursor: str | None = Query(None), limit: int = Query(50, ge=1, le=100), db: Session = Depends(get_session), ctx: AuthContext = Depends(auth_context)):
    op(ctx, "listCases"); return page(list_entities(db, ctx, "ClinicalCase"), ctx=ctx, route="listCases", cursor=cursor, limit=limit)


@router.get("/cases/{case_id}")
def get_case(case_id: str, db: Session = Depends(get_session), ctx: AuthContext = Depends(auth_context)):
    op(ctx, "getCase"); item = get_entity(db, ctx, "ClinicalCase", case_id); return response(item, etag=str(item["revision"]))


@router.post("/cases/{case_id}/transitions")
def transition_case(case_id: str, request: Request, body: dict = Body(...), idempotency_key: str | None = Header(None, alias="Idempotency-Key"), if_match: str | None = Header(None, alias="If-Match"), db: Session = Depends(get_session), ctx: AuthContext = Depends(auth_context)):
    op(ctx, "transitionCase"); validate("CaseTransition", body)
    allowed = {"draft": {"active", "cancelled"}, "active": {"waiting", "closed", "cancelled"}, "waiting": {"active", "closed", "cancelled"}, "closed": {"active"}, "cancelled": set()}
    def action():
        row = get_row(db, ctx, "ClinicalCase", case_id, for_update=True); enforce_match(row, if_match)
        current, target = row.data["lifecycle"], body["target"]
        if target not in allowed.get(current, set()):
            raise DomainError("workflow_transition_forbidden", 409, "Transition de cas interdite depuis l'état courant.")
        item = update_row(row, lifecycle=target)
        emit_event(db, ctx, "case.changed", "ClinicalCase", case_id, item["revision"], correlation(request), {"case_id": case_id, "target": target, "reason": body["reason"]})
        return item, 200, str(item["revision"])
    payload, status, etag = idempotent(db, ctx, "transitionCase", idempotency_key, body, action)
    return response(payload, status, etag)


def _record_observation(db: Session, ctx: AuthContext, case_row: Entity, body: dict, corr: str) -> dict:
    source = body["source"]
    new_id = uuid4()
    namespace = f"observation:{source['source_id']}"
    duplicate_id = register_external_version(db, ctx, namespace, source["record_id"], source["source_version"], body, new_id)
    if duplicate_id:
        return get_entity(db, ctx, "Observation", duplicate_id)
    obs = create_entity(db, ctx, "Observation", {"case_id": case_row.id, "recorded_at": now_iso(), "replaces_id": None, **body}, parent_id=case_row.id, status=body["status"], entity_id=new_id)
    case = update_row(case_row)
    stale_case_dependents(db, ctx, case_row.id, case["revision"])
    emit_event(db, ctx, "observation.recorded", "Observation", obs["id"], obs["revision"], corr, {"observation_id": obs["id"], "case_id": case_row.id})
    return obs


@router.post("/cases/{case_id}/observations")
def record_observation(case_id: str, request: Request, body: dict = Body(...), idempotency_key: str | None = Header(None, alias="Idempotency-Key"), if_match: str | None = Header(None, alias="If-Match"), db: Session = Depends(get_session), ctx: AuthContext = Depends(auth_context)):
    op(ctx, "recordObservation"); validate("RecordObservation", body)
    def action():
        case_row = get_row(db, ctx, "ClinicalCase", case_id, for_update=True); enforce_match(case_row, if_match)
        item = _record_observation(db, ctx, case_row, body, correlation(request))
        return item, 200, str(item["revision"])
    payload, status, etag = idempotent(db, ctx, "recordObservation", idempotency_key, body, action)
    return response(payload, status, etag)


@router.get("/cases/{case_id}/observations")
def list_observations(case_id: str, cursor: str | None = Query(None), limit: int = Query(50, ge=1, le=100), db: Session = Depends(get_session), ctx: AuthContext = Depends(auth_context)):
    op(ctx, "listObservations")
    get_row(db, ctx, "ClinicalCase", case_id)
    items = list_entities(db, ctx, "Observation", parent_id=case_id)
    items.sort(key=lambda item: (_ts(item["effective_at"]), item["recorded_at"], item["id"]))
    return page(items, ctx=ctx, route="listObservations", cursor=cursor, limit=limit, scope={"case_id": case_id})


@router.post("/observations/{observation_id}/amendments")
def amend_observation(observation_id: str, request: Request, body: dict = Body(...), idempotency_key: str | None = Header(None, alias="Idempotency-Key"), if_match: str | None = Header(None, alias="If-Match"), db: Session = Depends(get_session), ctx: AuthContext = Depends(auth_context)):
    op(ctx, "amendObservation"); validate("AmendObservation", body)
    def action():
        old_row = get_row(db, ctx, "Observation", observation_id, for_update=True); enforce_match(old_row, if_match)
        case_row = get_row(db, ctx, "ClinicalCase", old_row.parent_id, for_update=True)
        replacement = body["replacement"]
        new_obs = create_entity(db, ctx, "Observation", {"case_id": case_row.id, "recorded_at": now_iso(), "replaces_id": observation_id, **replacement}, parent_id=case_row.id, status=replacement["status"])
        update_row(old_row, status="amended")
        case = update_row(case_row)
        stale_case_dependents(db, ctx, case_row.id, case["revision"])
        emit_event(db, ctx, "observation.amended", "Observation", new_obs["id"], new_obs["revision"], correlation(request), {"observation_id": new_obs["id"], "replaces_id": observation_id, "reason": body["reason"]})
        return new_obs, 200, str(new_obs["revision"])
    payload, status, etag = idempotent(db, ctx, "amendObservation", idempotency_key, body, action)
    return response(payload, status, etag)


@router.post("/cases/{case_id}/evaluations")
def evaluate_case(case_id: str, request: Request, body: dict = Body(...), idempotency_key: str | None = Header(None, alias="Idempotency-Key"), if_match: str | None = Header(None, alias="If-Match"), db: Session = Depends(get_session), ctx: AuthContext = Depends(auth_context)):
    op(ctx, "evaluateCase"); validate("EvaluationRequest", body)
    def action():
        case_row = get_row(db, ctx, "ClinicalCase", case_id, for_update=True); enforce_match(case_row, if_match); require_case_revision(case_row, body["case_revision"])
        _require_evaluation_artifacts(db, ctx, body)
        if body["intended_use"] != case_row.data.get("intended_use"):
            raise DomainError("authorization_scope_mismatch", 403, "La finalité d'évaluation doit correspondre à celle du cas.")
        observations = list_entities(db, ctx, "Observation", parent_id=case_id)
        ev_payload = syn.evaluate(case_row.data, observations, body)
        ev = create_entity(db, ctx, "Evaluation", ev_payload, parent_id=case_id, status=ev_payload["status"])
        for proposal in syn.proposals_for(ev):
            create_entity(db, ctx, "ActionProposal", proposal, parent_id=case_id, status="proposed")
        operation = make_operation(db, ctx, "evaluate_case", ev["id"], correlation(request))
        emit_event(db, ctx, "evaluation.completed", "Evaluation", ev["id"], ev["revision"], correlation(request), {"evaluation_id": ev["id"], "status": ev["status"]})
        return operation, 202, str(operation["revision"])
    payload, status, etag = idempotent(db, ctx, "evaluateCase", idempotency_key, body, action)
    return response(payload, status, etag)


@router.get("/evaluations/{evaluation_id}")
def get_evaluation(evaluation_id: str, db: Session = Depends(get_session), ctx: AuthContext = Depends(auth_context)):
    op(ctx, "getEvaluation"); item = get_entity(db, ctx, "Evaluation", evaluation_id); return response(item, etag=str(item["revision"]))


@router.get("/cases/{case_id}/proposals")
def list_proposals(case_id: str, cursor: str | None = Query(None), limit: int = Query(50, ge=1, le=100), db: Session = Depends(get_session), ctx: AuthContext = Depends(auth_context)):
    op(ctx, "listProposals"); get_row(db, ctx, "ClinicalCase", case_id); return page(list_entities(db, ctx, "ActionProposal", parent_id=case_id), ctx=ctx, route="listProposals", cursor=cursor, limit=limit, scope={"case_id": case_id})


@router.post("/proposals/{proposal_id}/decisions")
def decide_proposal(proposal_id: str, request: Request, body: dict = Body(...), idempotency_key: str | None = Header(None, alias="Idempotency-Key"), if_match: str | None = Header(None, alias="If-Match"), db: Session = Depends(get_session), ctx: AuthContext = Depends(auth_context)):
    op(ctx, "decideProposal"); validate("ProposalDecision", body)
    def action():
        row = get_row(db, ctx, "ActionProposal", proposal_id, for_update=True); enforce_match(row, if_match)
        case = get_row(db, ctx, "ClinicalCase", row.parent_id)
        if row.data["case_revision"] != case.revision:
            raise DomainError("stale_case", 409, "La proposition est fondée sur une ancienne révision du cas.")
        if row.data["status"] != "proposed": raise DomainError("workflow_transition_forbidden", 409, "La proposition n'est plus décidable.")
        item = update_row(row, status="accepted" if body["decision"] == "accept" else "rejected")
        emit_event(db,ctx,"proposal.changed","ActionProposal",row.id,item["revision"],correlation(request),{"status":item["status"],"decision":body["decision"]})
        return item, 200, str(item["revision"])
    payload, status, etag = idempotent(db, ctx, "decideProposal", idempotency_key, body, action)
    return response(payload, status, etag)


@router.post("/plans")
def compare_plans(request: Request, body: dict = Body(...), idempotency_key: str | None = Header(None, alias="Idempotency-Key"), db: Session = Depends(get_session), ctx: AuthContext = Depends(auth_context)):
    op(ctx, "comparePlans"); validate("PlanRequest", body)
    def action():
        case = get_row(db, ctx, "ClinicalCase", body["case_id"]); require_case_revision(case, body["case_revision"])
        evaluation = get_row(db, ctx, "Evaluation", body["evaluation_id"])
        if evaluation.parent_id != case.id or evaluation.data.get("stale"):
            raise DomainError("stale_case", 409, "Évaluation périmée ou étrangère au cas.")
        _require_known_ref(body["policy_ref"], syn.optimization_policies(), "politique d'optimisation")

        now = datetime.now(timezone.utc)
        snapshots: list[Entity] = []
        capability_by_snapshot: dict[str, Entity] = {}
        valid_until = now + timedelta(hours=1)
        for snapshot_id in body["resource_snapshot_ids"]:
            snap = get_row(db, ctx, "AvailabilitySnapshot", snapshot_id)
            if _ts(snap.data["valid_until"]) <= now:
                raise DomainError("stale_availability", 409, "Un snapshot de ressource est expiré.")
            cap = get_row(db, ctx, "ResourceCapability", snap.parent_id)
            snapshots.append(snap); capability_by_snapshot[snap.id] = cap
            valid_until = min(valid_until, _ts(snap.data["valid_until"]))

        all_quotes = list_entities(db, ctx, "CostQuote")
        comparisons = []
        strategies = []
        cost_refs_by_digest: dict[str, dict] = {}
        for proposal_id in body["proposal_ids"]:
            p = get_row(db, ctx, "ActionProposal", proposal_id)
            if p.parent_id != case.id:
                raise DomainError("authorization_scope_mismatch", 403, "Proposition hors du cas.")
            if p.data.get("case_revision") != case.revision or p.data.get("status") not in {"proposed", "accepted"}:
                raise DomainError("stale_case", 409, "Proposition périmée ou non admissible au calcul.")
            strategy = artifact_ref(f"proposal:{proposal_id}")
            strategies.append(strategy["id"])
            criteria: list[dict] = []
            admissible = True
            reasons = ["synthetic_comparison"]

            if p.data["kind"] == "test":
                matching: list[tuple[Entity, Entity]] = []
                for snap in snapshots:
                    cap = capability_by_snapshot[snap.id]
                    if cap.data.get("procedure") != p.data.get("target"):
                        continue
                    free = any(slot.get("state") == "free" and int(slot.get("remaining_capacity", 0)) > 0 and _ts(slot["end"]) > now for slot in snap.data.get("slots", []))
                    if free:
                        matching.append((snap, cap))
                if not matching:
                    admissible = False
                    reasons.append("capacity_unavailable")
                    criteria.append({"criterion_ref": artifact_ref("availability"), "state": "known", "value": 0.0, "unit": "available_capacity", "source_refs": []})
                else:
                    criteria.append({"criterion_ref": artifact_ref("availability"), "state": "known", "value": 1.0, "unit": "available_capacity", "source_refs": [{"id":f"availability:{snap.id}","version":str(snap.revision),"digest":digest(snap.data)} for snap,_ in matching]})

                capability_ids = {cap.id for _, cap in matching}
                quotes = [q for q in all_quotes if q.get("capability_id") in capability_ids and _ts(q["valid_from"]) <= now < _ts(q["valid_until"])]
                if not quotes:
                    criteria.append({"criterion_ref": artifact_ref("cost"), "state": "unknown", "value": None, "unit": "minor_currency_unit", "source_refs": []})
                else:
                    # Separate economic perspectives and currencies are independent criteria;
                    # they are never added together implicitly.
                    grouped: dict[tuple[str,str,str], list[dict]] = {}
                    for quote in quotes:
                        grouped.setdefault((quote["perspective"], quote["currency"], quote["kind"]), []).append(quote)
                    for (perspective,currency,kind), group in sorted(grouped.items()):
                        selected = min(group, key=lambda q: (q["amount_minor"], q["id"]))
                        ref={"id":f"cost-quote:{selected['id']}","version":str(selected["revision"]),"digest":digest(selected)}
                        cost_refs_by_digest[ref["digest"]]=ref
                        valid_until=min(valid_until,_ts(selected["valid_until"]))
                        criteria.append({
                            "criterion_ref": artifact_ref(f"cost:{perspective}:{kind}:{currency}"),
                            "state":"known","value":float(selected["amount_minor"]),"unit":currency,"source_refs":[ref],
                        })
            else:
                criteria.append({"criterion_ref": artifact_ref("resource_requirement"), "state": "not_applicable", "value": None, "unit": "resource", "source_refs": []})

            comparisons.append({"strategy_ref": strategy, "admissible": admissible, "reason_codes": reasons, "criteria": criteria, "dominated_by": []})

        feasible = [c for c in comparisons if c["admissible"]]
        status = "feasible" if feasible else ("infeasible" if comparisons else "unknown")
        plan_payload = {
            "case_id": case.id, "case_revision": case.revision, "status": status,
            "strategy_refs": strategies, "selected_strategy_ref": None,
            "limitations": ["Front synthétique; aucun résultat clinique ou coût inconnu n'est inventé."], "policy_ref": body["policy_ref"],
            "resource_snapshot_ids": body["resource_snapshot_ids"],
            "explanation": "Les contraintes de capacité sont appliquées avant les coûts; devises et perspectives restent séparées.",
            "comparisons": comparisons, "cost_snapshot_refs": list(cost_refs_by_digest.values()), "computed_at": now_iso(),
            "valid_until": valid_until.isoformat().replace("+00:00","Z"),
        }
        validate("Plan", {"id":uuid4(),"tenant_id":ctx.tenant_id,"revision":1,"created_at":now_iso(),"updated_at":now_iso(),**plan_payload})
        plan_item = create_entity(db, ctx, "Plan", plan_payload, parent_id=case.id, status=plan_payload["status"])
        emit_event(db,ctx,"plan.computed","Plan",plan_item["id"],plan_item["revision"],correlation(request),{"case_id":case.id,"status":plan_item["status"]})
        operation = make_operation(db, ctx, "compare_plans", plan_item["id"], correlation(request))
        return operation, 202, str(operation["revision"])
    payload, status, etag = idempotent(db, ctx, "comparePlans", idempotency_key, body, action)
    return response(payload, status, etag)


@router.get("/plans/{plan_id}")
def get_plan(plan_id: str, db: Session = Depends(get_session), ctx: AuthContext = Depends(auth_context)):
    op(ctx, "getPlan"); item = get_entity(db, ctx, "Plan", plan_id); return response(item, etag=str(item["revision"]))


@router.post("/orders")
def request_order(request: Request, body: dict = Body(...), idempotency_key: str | None = Header(None, alias="Idempotency-Key"), db: Session = Depends(get_session), ctx: AuthContext = Depends(auth_context)):
    op(ctx, "requestOrder"); validate("OrderRequest", body)
    def action():
        proposal = get_row(db, ctx, "ActionProposal", body["proposal_id"], for_update=True)
        case = get_row(db, ctx, "ClinicalCase", proposal.parent_id)
        require_case_revision(case, body["case_revision"])
        if proposal.data["status"] != "accepted": raise DomainError("permission_denied", 403, "La proposition doit être acceptée avant une demande d'ordre.")
        cfg, _ = get_configuration(db, ctx, settings.configuration_default)
        if cfg["execution_policy"] != "protocol_authorized": raise DomainError("clinical_use_not_admitted", 403, "La politique courante autorise seulement les propositions.")
        if not _same_artifact_ref(body["authorization_policy_ref"], syn.AUTH_POLICY) or case.data.get("intended_use") != "engineering":
            raise DomainError("clinical_use_not_admitted", 403, "Aucune délégation clinique réelle n'est livrée.")
        order = create_entity(db, ctx, "ServiceOrder", {"proposal_id": proposal.id, "case_id": case.id, "case_revision": case.revision, "destination": body["destination"], "status": "requested", "foreign_ref": None}, parent_id=case.id, status="requested")
        update_row(proposal, status="order_requested")
        operation = make_operation(db, ctx, "request_order", order["id"], correlation(request), status="succeeded")
        emit_event(db, ctx, "order.requested", "ServiceOrder", order["id"], order["revision"], correlation(request), {"order_id": order["id"]})
        return operation, 202, str(operation["revision"])
    payload, status, etag = idempotent(db, ctx, "requestOrder", idempotency_key, body, action)
    return response(payload, status, etag)


@router.get("/orders/{order_id}")
def get_order(order_id: str, db: Session = Depends(get_session), ctx: AuthContext = Depends(auth_context)):
    op(ctx, "getOrder"); item = get_entity(db, ctx, "ServiceOrder", order_id); return response(item, etag=str(item["revision"]))


@router.post("/resource-capabilities")
def create_resource_capability(request: Request, body: dict = Body(...), idempotency_key: str | None = Header(None, alias="Idempotency-Key"), db: Session = Depends(get_session), ctx: AuthContext = Depends(auth_context)):
    op(ctx, "createResourceCapability"); validate("CapabilityInput", body)
    def action():
        _validate_capability_refs(db, ctx, body)
        item = create_entity(db, ctx, "ResourceCapability", body)
        emit_event(db,ctx,"catalog.changed","ResourceCapability",item["id"],item["revision"],correlation(request),{"reason":"created"})
        return item, 201, str(item["revision"])
    p,s,e=idempotent(db,ctx,"createResourceCapability",idempotency_key,body,action); return response(p,s,e)


@router.get("/resource-capabilities")
def list_resource_capabilities(cursor: str | None = Query(None), limit: int = Query(50, ge=1, le=100), db: Session = Depends(get_session), ctx: AuthContext = Depends(auth_context)):
    op(ctx, "listResourceCapabilities"); return page(list_entities(db, ctx, "ResourceCapability"), ctx=ctx, route="listResourceCapabilities", cursor=cursor, limit=limit)


@router.get("/resource-capabilities/{capability_id}")
def get_resource_capability(capability_id: str, db: Session = Depends(get_session), ctx: AuthContext = Depends(auth_context)):
    op(ctx,"getResourceCapability"); item=get_entity(db,ctx,"ResourceCapability",capability_id); return response(item,etag=str(item["revision"]))


@router.post("/resource-capabilities/{capability_id}/revisions")
def revise_resource_capability(capability_id: str, request: Request, body: dict=Body(...), idempotency_key: str|None=Header(None,alias="Idempotency-Key"), if_match: str|None=Header(None,alias="If-Match"), db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"reviseResourceCapability"); validate("CapabilityRevision",body)
    def action():
        row=get_row(db,ctx,"ResourceCapability",capability_id,for_update=True); enforce_match(row,if_match)
        _validate_capability_refs(db,ctx,body["replacement"])
        item=update_row(row,replacement=body["replacement"])
        emit_event(db,ctx,"catalog.changed","ResourceCapability",capability_id,item["revision"],correlation(request),{"reason":body["reason"]})
        return item,200,str(item["revision"])
    p,s,e=idempotent(db,ctx,"reviseResourceCapability",idempotency_key,body,action); return response(p,s,e)


@router.post("/resource-capabilities/{capability_id}/availability")
def record_availability(capability_id: str, request: Request, body: dict=Body(...), idempotency_key: str|None=Header(None,alias="Idempotency-Key"), db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"recordAvailability"); validate("AvailabilityInput",body)
    def action():
        capability=get_row(db,ctx,"ResourceCapability",capability_id)
        if _ts(body["captured_at"]) >= _ts(body["valid_until"]):
            raise DomainError("invalid_request",422,"valid_until doit être postérieur à captured_at.")
        seen_slots=set()
        valid_until = _ts(body["valid_until"])
        for slot in body["slots"]:
            start, end = _ts(slot["start"]), _ts(slot["end"])
            if start >= end: raise DomainError("invalid_request",422,"Un créneau doit avoir start < end.")
            if end > valid_until: raise DomainError("invalid_request",422,"Un créneau ne peut pas dépasser la validité du snapshot.")
            if slot["slot_id"] in seen_slots: raise DomainError("invalid_request",422,"Deux créneaux ne peuvent partager le même slot_id dans un snapshot.")
            seen_slots.add(slot["slot_id"])
            if slot["remaining_capacity"] > int(capability.data.get("capacity",1)):
                raise DomainError("invalid_request",422,"remaining_capacity dépasse la capacité déclarée.")
            if slot["state"] in {"booked", "unavailable"} and slot["remaining_capacity"] != 0:
                raise DomainError("invalid_request",422,"Un créneau booked/unavailable doit avoir une capacité restante nulle.")
        item=create_entity(db,ctx,"AvailabilitySnapshot",{"capability_id":capability_id,**body},parent_id=capability_id)
        emit_event(db,ctx,"availability.recorded","AvailabilitySnapshot",item["id"],item["revision"],correlation(request),{"capability_id":capability_id,"owner":body["owner"]})
        return item,201,str(item["revision"])
    p,s,e=idempotent(db,ctx,"recordAvailability",idempotency_key,body,action); return response(p,s,e)


@router.get("/resource-capabilities/{capability_id}/availability")
def get_availability(capability_id:str, db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"getAvailability"); get_row(db,ctx,"ResourceCapability",capability_id)
    items=list_entities(db,ctx,"AvailabilitySnapshot",parent_id=capability_id)
    if not items: raise DomainError("stale_availability",404,"Aucun snapshot de disponibilité n'est disponible.")
    item=items[-1]; return response(item,etag=str(item["revision"]))


@router.post("/cost-quotes")
def create_cost_quote(request:Request, body:dict=Body(...), idempotency_key:str|None=Header(None,alias="Idempotency-Key"), db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"createCostQuote"); validate("CostInput",body)
    def action():
        get_row(db,ctx,"ResourceCapability",body["capability_id"])
        if _ts(body["valid_from"]) >= _ts(body["valid_until"]):
            raise DomainError("invalid_request",422,"valid_until doit être postérieur à valid_from.")
        item=create_entity(db,ctx,"CostQuote",body,parent_id=body["capability_id"])
        emit_event(db,ctx,"cost_quote.changed","CostQuote",item["id"],item["revision"],correlation(request),{"capability_id":body["capability_id"]})
        return item,201,str(item["revision"])
    p,s,e=idempotent(db,ctx,"createCostQuote",idempotency_key,body,action); return response(p,s,e)


@router.get("/cost-quotes")
def list_cost_quotes(cursor:str|None=Query(None), limit:int=Query(50,ge=1,le=100), capability_id:str|None=Query(None), db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"listCostQuotes"); items=list_entities(db,ctx,"CostQuote",parent_id=capability_id) if capability_id else list_entities(db,ctx,"CostQuote"); return page(items,ctx=ctx,route="listCostQuotes",cursor=cursor,limit=limit,scope={"capability_id":capability_id})


@router.post("/bookings")
def request_booking(request:Request, body:dict=Body(...), idempotency_key:str|None=Header(None,alias="Idempotency-Key"), db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"requestBooking"); validate("BookingRequest",body)
    def action():
        order=get_row(db,ctx,"ServiceOrder",body["order_id"])
        if order.data.get("status") not in {"requested","accepted","in_progress"}:
            raise DomainError("booking_conflict",409,"L'ordre n'est pas dans un état réservable.")
        capability=get_row(db,ctx,"ResourceCapability",body["capability_id"],for_update=True)
        proposal=db.execute(select(Entity).where(
            Entity.tenant_id==ctx.tenant_id, Entity.kind=="ActionProposal", Entity.id==order.data.get("proposal_id")
        )).scalar_one_or_none()
        if proposal is not None and proposal.data.get("kind") == "test" and capability.data.get("procedure") != proposal.data.get("target"):
            raise DomainError("authorization_scope_mismatch",403,"La capacité ne correspond pas à l'acte de la proposition ordonnée.")
        snap=get_row(db,ctx,"AvailabilitySnapshot",body["availability_snapshot_id"])
        if snap.parent_id!=capability.id: raise DomainError("authorization_scope_mismatch",403,"Snapshot hors de la capacité.")
        if _ts(snap.data["valid_until"]) <= datetime.now(timezone.utc):
            raise DomainError("stale_availability",409,"Le snapshot de disponibilité est expiré.")
        slot=next((x for x in snap.data["slots"] if x["slot_id"]==body["slot_id"]),None)
        if slot is None or slot["state"] not in {"free","held"} or slot["remaining_capacity"]<1:
            raise DomainError("booking_conflict",409,"Créneau non attribuable.")
        if _ts(slot["end"]) <= datetime.now(timezone.utc):
            raise DomainError("stale_availability",409,"Le créneau est déjà terminé.")

        booking_id=uuid4()
        max_units=min(int(slot["remaining_capacity"]), int(capability.data.get("capacity",1)))
        claimed_unit=None
        for unit_index in range(1,max_units+1):
            try:
                with db.begin_nested():
                    db.add(ReservationClaim(
                        id=uuid4(),tenant_id=ctx.tenant_id,capability_id=capability.id,
                        slot_id=body["slot_id"],unit_index=unit_index,booking_id=booking_id,created_at=utcnow(),
                    ))
                    db.flush()
                claimed_unit=unit_index
                break
            except IntegrityError:
                continue
        if claimed_unit is None:
            raise DomainError("booking_conflict",409,"La capacité restante du créneau est déjà attribuée.")

        booking=create_entity(db,ctx,"Booking",{
            "order_id":order.id,"capability_id":capability.id,"slot_id":body["slot_id"],
            "owner":snap.data["owner"],"status":"held","hold_expires_at":snap.data["valid_until"],
            "foreign_ref":{"owner":snap.data["owner"],"id":f"hold-{uuid4()}","version":"1"},
        },parent_id=order.id,status="held",foreign_key=f"{capability.id}:{body['slot_id']}:{claimed_unit}",entity_id=booking_id)
        operation=make_operation(db,ctx,"request_booking",booking["id"],correlation(request))
        emit_event(db,ctx,"booking.updated","Booking",booking["id"],booking["revision"],correlation(request),{"status":"held","capacity_unit":claimed_unit})
        return operation,202,str(operation["revision"])
    p,s,e=idempotent(db,ctx,"requestBooking",idempotency_key,body,action); return response(p,s,e)


@router.get("/bookings/{booking_id}")
def get_booking(booking_id:str, db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"getBooking"); item=get_entity(db,ctx,"Booking",booking_id); return response(item,etag=str(item["revision"]))


@router.post("/bookings/{booking_id}/confirmations")
def confirm_booking(booking_id:str, request:Request, body:dict=Body(...), idempotency_key:str|None=Header(None,alias="Idempotency-Key"), if_match:str|None=Header(None,alias="If-Match"), db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"confirmBooking"); validate("ReasonCommand",body)
    def action():
        row=get_row(db,ctx,"Booking",booking_id,for_update=True); enforce_match(row,if_match)
        if row.data["status"] not in {"held","confirm_requested","reconciling"}:
            raise DomainError("booking_conflict",409,"Réservation non confirmable.")
        if row.data.get("hold_expires_at") and _ts(row.data["hold_expires_at"]) <= datetime.now(timezone.utc):
            item=update_row(row,status="expired")
            db.execute(delete(ReservationClaim).where(ReservationClaim.tenant_id==ctx.tenant_id,ReservationClaim.booking_id==booking_id))
            operation=make_operation(db,ctx,"confirm_booking",booking_id,correlation(request),status="failed",error_code="stale_availability")
            emit_event(db,ctx,"booking.updated","Booking",booking_id,item["revision"],correlation(request),{"status":"expired"})
            return operation,202,str(operation["revision"])
        if row.data["status"]=="held":
            update_row(row,status="confirm_requested")
        try:
            facility_adapter(row.data["owner"]).confirm({
                "booking_id": booking_id, "foreign_ref": row.data.get("foreign_ref"), "reason": body["reason"],
            })
            item=update_row(row,status="confirmed")
            operation=make_operation(db,ctx,"confirm_booking",booking_id,correlation(request))
        except DomainError as exc:
            if exc.code != "capability_unavailable":
                raise
            # The booking/claim already exists but the external owner cannot be queried.
            # Preserve it and require reconciliation rather than inventing success or retrying.
            item=update_row(row,status="reconciling")
            operation=make_operation(db,ctx,"confirm_booking",booking_id,correlation(request),status="reconciling",error_code="provider_outcome_unknown")
        emit_event(db,ctx,"booking.updated","Booking",booking_id,item["revision"],correlation(request),{"status":item["status"]})
        return operation,202,str(operation["revision"])
    p,s,e=idempotent(db,ctx,"confirmBooking",idempotency_key,body,action); return response(p,s,e)


@router.post("/bookings/{booking_id}/cancellations")
def cancel_booking(booking_id:str, request:Request, body:dict=Body(...), idempotency_key:str|None=Header(None,alias="Idempotency-Key"), if_match:str|None=Header(None,alias="If-Match"), db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"cancelBooking"); validate("ReasonCommand",body)
    def action():
        row=get_row(db,ctx,"Booking",booking_id,for_update=True); enforce_match(row,if_match)
        if row.data["status"] in {"cancelled","expired","rejected"}: raise DomainError("booking_conflict",409,"Réservation déjà terminale.")
        if row.data["status"]!="reconciling":
            update_row(row,status="cancel_requested")
        try:
            facility_adapter(row.data["owner"]).cancel({
                "booking_id": booking_id, "foreign_ref": row.data.get("foreign_ref"), "reason": body["reason"],
            })
            item=update_row(row,status="cancelled")
            db.execute(delete(ReservationClaim).where(ReservationClaim.tenant_id==ctx.tenant_id,ReservationClaim.booking_id==booking_id))
            operation=make_operation(db,ctx,"cancel_booking",booking_id,correlation(request),status="succeeded")
        except DomainError as exc:
            if exc.code != "capability_unavailable":
                raise
            item=update_row(row,status="reconciling")
            operation=make_operation(db,ctx,"cancel_booking",booking_id,correlation(request),status="reconciling",error_code="provider_outcome_unknown")
        emit_event(db,ctx,"booking.updated","Booking",booking_id,item["revision"],correlation(request),{"status":item["status"],"reason":body["reason"]})
        return operation,202,str(operation["revision"])
    p,s,e=idempotent(db,ctx,"cancelBooking",idempotency_key,body,action); return response(p,s,e)


@router.post("/sources")
def register_source(request:Request, body:dict=Body(...), idempotency_key:str|None=Header(None,alias="Idempotency-Key"), db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"registerSource"); validate("SourceRegistration",body)
    def action():
        item=create_entity(db,ctx,"Source",body)
        emit_event(db,ctx,"source.registered","Source",item["id"],item["revision"],correlation(request),{"source_id":item["id"]})
        return item,201,str(item["revision"])
    p,s,e=idempotent(db,ctx,"registerSource",idempotency_key,body,action); return response(p,s,e)


@router.get("/sources")
def list_sources(cursor:str|None=Query(None), limit:int=Query(50,ge=1,le=100), db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"listSources"); return page(list_entities(db,ctx,"Source"),ctx=ctx,route="listSources",cursor=cursor,limit=limit)


@router.get("/sources/{source_id}")
def get_source(source_id:str, db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"getSource"); item=get_entity(db,ctx,"Source",source_id); return response(item,etag=str(item["revision"]))


def _store_import_issues(db: Session, ctx: AuthContext, run: Entity, issues: list[dict]) -> None:
    for index, issue in enumerate(issues):
        create_entity(db, ctx, "ImportIssue", {
            "import_run_id": run.id,
            "source_id": run.data["source_id"],
            "record_ref": issue["record_ref"],
            "code": issue["code"],
            "severity": issue["severity"],
            "detail": issue["detail"],
        }, parent_id=run.id, status=issue["severity"], foreign_key=f"{run.id}:issue:{index}")


def _store_import_records(
    db: Session,
    ctx: AuthContext,
    parent: Entity,
    parsed,
    *,
    source_id: str,
    source_version: str,
    status: str,
) -> None:
    normalized_by_line = {int(row["_line"]): row for row in parsed.rows}
    for raw in parsed.raw_records:
        line = int(raw["line"])
        normalized = normalized_by_line.get(line)
        record = create_entity(db, ctx, "RawRecord", {
            "source_id": source_id,
            "source_version": source_version,
            "profile": parsed.profile,
            "line": line,
            "raw": raw["fields"],
            "raw_digest": digest(raw["fields"]),
            "normalized": ({k: v for k, v in normalized.items() if k not in {"_raw", "_line"}} if normalized else None),
        }, parent_id=parent.id, status=status, foreign_key=f"{parent.id}:raw:{line}")
        if normalized is not None:
            create_entity(db, ctx, "MappingCandidate", {
                "source_id": source_id,
                "source_version": source_version,
                "candidate_type": f"local_catalog_{parsed.kind}",
                "source_record_id": record["id"],
                "normalized": {k: v for k, v in normalized.items() if k not in {"_raw", "_line"}},
                "mapping_version": MAPPING_VERSION,
                "status": status,
            }, parent_id=parent.id, status=status, foreign_key=f"{parent.id}:candidate:{line}")


@router.post("/sources/{source_id}/imports")
def import_source(source_id:str, request:Request, body:dict=Body(...), idempotency_key:str|None=Header(None,alias="Idempotency-Key"), db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"importSource"); validate("ImportRequest",body)
    def action():
        src=get_row(db,ctx,"Source",source_id)
        run_data=create_entity(db,ctx,"ImportRun",{
            "source_id":source_id,"source_version":body["source_version"],"blob_digest":body["expected_digest"],
            "parser_version":PARSER_VERSION,"mapping_version":MAPPING_VERSION,"status":"received",
            "checkpoint":{"stage":"received","record_index":0},"snapshot_id":None,
        },parent_id=source_id,status="received")
        run=get_row(db,ctx,"ImportRun",run_data["id"],for_update=True)
        if src.data.get("source_type")!="local_catalog":
            issue={"record_ref":body["uploaded_file_ref"],"code":"unsupported_profile","severity":"error",
                   "detail":"Aucun parseur qualifié n'est livré pour ce type de source dans cette distribution."}
            _store_import_issues(db,ctx,run,[issue])
            update_row(run,status="failed",checkpoint={"stage":"failed","record_index":0})
            operation=make_operation(db,ctx,"import_source",None,correlation(request),status="failed",error_code="capability_unavailable")
            report=create_entity(db,ctx,"ImportReport",{
                "source_id":source_id,"operation_id":operation["id"],"status":"failed","read_count":0,
                "normalized_count":0,"rejected_count":0,"issues":[issue],"artifact_ref":None,
            },parent_id=source_id,status="failed")
            op_row=get_row(db,ctx,"Operation",operation["id"],for_update=True); item=update_row(op_row,result_ref=report["id"])
            return item,202,str(item["revision"])

        blob=resolve_blob(db,ctx,body["uploaded_file_ref"],body["expected_digest"])
        update_row(run,status="verified",checkpoint={"stage":"verified","record_index":0})
        parsed=parse_local_catalog_csv(blob.content)
        update_row(run,status="parsed",checkpoint={"stage":"parsed","record_index":len(parsed.raw_records)})
        errors=[i for i in parsed.issues if i["severity"]=="error"]
        if errors:
            _store_import_records(db,ctx,run,parsed,source_id=source_id,source_version=body["source_version"],status="quarantined")
            _store_import_issues(db,ctx,run,parsed.issues)
            update_row(run,status="quarantined",checkpoint={"stage":"quarantined","record_index":len(parsed.raw_records)})
            operation=make_operation(db,ctx,"import_source",None,correlation(request),status="failed",error_code=errors[0]["code"])
            report=create_entity(db,ctx,"ImportReport",{
                "source_id":source_id,"operation_id":operation["id"],"status":"quarantined",
                "read_count":len(parsed.raw_records),"normalized_count":0,"rejected_count":len(errors),
                "issues":parsed.issues,"artifact_ref":None,
            },parent_id=source_id,status="quarantined")
            op_row=get_row(db,ctx,"Operation",operation["id"],for_update=True); item=update_row(op_row,result_ref=report["id"])
            return item,202,str(item["revision"])

        # Same logical source version with another blob is a conflict. A replay of the
        # same blob reuses the immutable snapshot and does not duplicate normalized rows.
        version_rows=db.execute(select(Entity).where(
            Entity.tenant_id==ctx.tenant_id,Entity.kind=="SourceSnapshot",Entity.parent_id==source_id,
        )).scalars().all()
        conflicting=next((r for r in version_rows if r.data.get("source_version")==body["source_version"] and r.data.get("blob_digest")!=blob.digest),None)
        if conflicting:
            raise DomainError("source_version_conflict",409,"Cette version de source existe déjà avec un digest différent.")
        update_row(run,status="normalized",checkpoint={"stage":"normalized","record_index":len(parsed.raw_records)})
        snapshot=existing_source_snapshot(db,ctx,source_id,body["source_version"],blob.digest)
        if snapshot is None:
            snapshot_data=create_entity(db,ctx,"SourceSnapshot",{
                "source_id":source_id,"source_version":body["source_version"],"blob_digest":blob.digest,
                "parser_version":PARSER_VERSION,"mapping_version":MAPPING_VERSION,"profile":parsed.profile,
                "kind":parsed.kind,"record_count":len(parsed.rows),"extra_columns":parsed.extra_columns,
                "rows":parsed.rows,
            },parent_id=source_id,status="reviewed",foreign_key=f"{source_id}:{body['source_version']}:{blob.digest}")
            snapshot=get_row(db,ctx,"SourceSnapshot",snapshot_data["id"])
            _store_import_records(db,ctx,snapshot,parsed,source_id=source_id,source_version=body["source_version"],status="reviewed")
        _store_import_issues(db,ctx,run,parsed.issues)
        update_row(run,status="reviewed",snapshot_id=snapshot.id,checkpoint={"stage":"reviewed","record_index":len(parsed.raw_records)})
        artifact={"id":f"source-snapshot:{snapshot.id}","version":body["source_version"],"digest":blob.digest}
        operation=make_operation(db,ctx,"import_source",None,correlation(request),status="succeeded")
        report=create_entity(db,ctx,"ImportReport",{
            "source_id":source_id,"operation_id":operation["id"],"status":"completed",
            "read_count":len(parsed.raw_records),"normalized_count":len(parsed.rows),"rejected_count":0,
            "issues":parsed.issues,"artifact_ref":artifact,
        },parent_id=source_id,status="completed")
        op_row=get_row(db,ctx,"Operation",operation["id"],for_update=True); item=update_row(op_row,result_ref=report["id"])
        emit_event(db,ctx,"import.completed","SourceSnapshot",snapshot.id,snapshot.revision,correlation(request),{
            "source_id":source_id,"source_version":body["source_version"],"snapshot_id":snapshot.id,
        })
        return item,202,str(item["revision"])
    p,s,e=idempotent(db,ctx,"importSource",idempotency_key,body,action); return response(p,s,e)


@router.get("/imports/{operation_id}/report")
def get_import_report(operation_id:str, db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"getImportReport"); operation=get_row(db,ctx,"Operation",operation_id); rid=operation.data.get("result_ref")
    if not rid: raise DomainError("not_found",404,"Rapport d'import absent.")
    item=get_entity(db,ctx,"ImportReport",rid); return response(item,etag=str(item["revision"]))


@router.get("/knowledge/concepts")
def search_concepts(q:str=Query(...,min_length=1), cursor:str|None=Query(None), limit:int=Query(50,ge=1,le=100), db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"searchConcepts")
    items=[syn.concept("SYN-D1"),syn.concept("SYN-T1"),syn.concept("SYN-DRUG"),syn.concept("SYN-Q1"),syn.concept("SYN-OBS1")]
    items=[x for x in items if q.lower() in x["code"].lower() or q.lower() in x["system"].lower()]
    return page(items,ctx=ctx,route="searchConcepts",cursor=cursor,limit=limit,scope={"q":q})


@router.get("/knowledge/assertions")
def search_assertions(cursor:str|None=Query(None), limit:int=Query(50,ge=1,le=100), subject_code:str|None=Query(None), predicate:str|None=Query(None), object_code:str|None=Query(None), release_id:str|None=Query(None), db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"searchAssertions")
    items=syn.assertions()
    if subject_code: items=[x for x in items if x["subject"]["code"]==subject_code]
    if predicate: items=[x for x in items if x["predicate"]==predicate]
    if object_code: items=[x for x in items if x["object"]["code"]==object_code]
    if release_id and release_id not in {syn.SYN_RELEASE["id"],syn.SYN_RELEASE["digest"]}: items=[]
    return page(items,ctx=ctx,route="searchAssertions",cursor=cursor,limit=limit,scope={"subject_code":subject_code,"predicate":predicate,"object_code":object_code,"release_id":release_id})


@router.get("/knowledge/models")
def list_models(cursor:str|None=Query(None), limit:int=Query(50,ge=1,le=100), release_id:str|None=Query(None), population_id:str|None=Query(None), db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"listModels"); items=syn.models()
    allowed=_release_refs(db,ctx,release_id,"model_refs")
    if allowed is not None: items=[x for x in items if (x["id"],x["version"],x["digest"]) in allowed]
    if population_id: items=[x for x in items if x["scope"]["population_id"]==population_id]
    return page(items,ctx=ctx,route="listModels",cursor=cursor,limit=limit,scope={"release_id":release_id,"population_id":population_id})


@router.get("/knowledge/protocols")
def list_protocols(cursor:str|None=Query(None), limit:int=Query(50,ge=1,le=100), release_id:str|None=Query(None), db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"listProtocols"); items=syn.protocols()
    allowed=_release_refs(db,ctx,release_id,"protocol_refs")
    if allowed is not None: items=[x for x in items if (x["id"],x["version"],x["digest"]) in allowed]
    return page(items,ctx=ctx,route="listProtocols",cursor=cursor,limit=limit,scope={"release_id":release_id})


@router.get("/knowledge/evidence")
def list_evidence(cursor:str|None=Query(None), limit:int=Query(50,ge=1,le=100), subject_code:str|None=Query(None), release_id:str|None=Query(None), db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"listEvidence")
    items=syn.evidence()
    if subject_code: items=[x for x in items if x["target"]["code"]==subject_code or (x.get("test") and x["test"]["code"]==subject_code)]
    if release_id and release_id not in {syn.SYN_RELEASE["id"],syn.SYN_RELEASE["digest"]}: items=[]
    return page(items,ctx=ctx,route="listEvidence",cursor=cursor,limit=limit,scope={"subject_code":subject_code,"release_id":release_id})


@router.get("/knowledge/optimization-policies")
def list_optimization_policies(cursor:str|None=Query(None), limit:int=Query(50,ge=1,le=100), db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"listOptimizationPolicies"); return page(syn.optimization_policies(),ctx=ctx,route="listOptimizationPolicies",cursor=cursor,limit=limit)


@router.post("/knowledge/releases")
def build_release(request:Request, body:dict=Body(...), idempotency_key:str|None=Header(None,alias="Idempotency-Key"), db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"buildRelease"); validate("ReleaseBuildRequest",body)
    def action():
        if not body["synthetic"] or body["intended_use"]!="engineering":
            raise DomainError("release_not_admitted",409,"Cette distribution ne construit que des releases synthétiques d'ingénierie.")
        for ref in body["model_refs"]:
            _require_known_ref(ref,syn.models(),"modèle")
        for ref in body["protocol_refs"]:
            _require_known_ref(ref,syn.protocols(),"protocole")
        for ref in body["source_snapshot_refs"]:
            if not ref["id"].startswith("source-snapshot:"):
                raise DomainError("not_found",404,"Snapshot de source introuvable.")
            snapshot_id=ref["id"].split(":",1)[1]
            snapshot=get_row(db,ctx,"SourceSnapshot",snapshot_id)
            if snapshot.data.get("source_version")!=ref["version"] or snapshot.data.get("blob_digest")!=ref["digest"]:
                raise DomainError("artifact_integrity_failed",422,"La référence du snapshot ne correspond pas au contenu importé.")
        rid=digest(body)
        existing=_release_row_by_digest(db,ctx,rid)
        if existing is None:
            release={"format":"medikristal.knowledge-release/1","release_id":rid,"version":"0.1.0","status":"candidate","usage":body["intended_use"],"synthetic":body["synthetic"],"files":[],"source_refs":body["source_snapshot_refs"],"model_refs":body["model_refs"],"protocol_refs":body["protocol_refs"],"rights_manifest_ref":syn.RIGHTS,"qualification_refs":[],"minimum_runtime":"0.1.0","built_at":now_iso(),"signatures":[]}
            validate("KnowledgeRelease",release)
            created=create_entity(db,ctx,"KnowledgeRelease",release,entity_id=uuid4(),envelope=False,status="candidate",foreign_key=rid)
            existing=_release_row_by_digest(db,ctx,rid)
            emit_event(db,ctx,"knowledge.release_built","KnowledgeRelease",existing.id,existing.revision,correlation(request),{"release_id":rid,"status":created["status"]})
        operation=make_operation(db,ctx,"build_release",existing.id,correlation(request)); return operation,202,str(operation["revision"])
    p,s,e=idempotent(db,ctx,"buildRelease",idempotency_key,body,action); return response(p,s,e)


@router.get("/knowledge/releases/{release_id}")
def get_release(release_id:str, db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"getRelease")
    row=db.execute(select(Entity).where(Entity.tenant_id==ctx.tenant_id,Entity.kind=="KnowledgeRelease",(Entity.id==release_id)|(Entity.foreign_key==release_id))).scalar_one_or_none()
    if not row: raise DomainError("not_found",404,"Release introuvable.")
    validate("KnowledgeRelease",row.data)
    return row.data


@router.post("/knowledge/releases/{release_id}/decisions")
def decide_release(release_id:str, request:Request, body:dict=Body(...), idempotency_key:str|None=Header(None,alias="Idempotency-Key"), db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"decideRelease"); validate("ReleaseDecision",body); _require_engineering_policy(body["policy_ref"])
    def action():
        row=db.execute(select(Entity).where(Entity.tenant_id==ctx.tenant_id,Entity.kind=="KnowledgeRelease",(Entity.id==release_id)|(Entity.foreign_key==release_id)).with_for_update()).scalar_one_or_none()
        if not row: raise DomainError("not_found",404,"Release introuvable.")
        current=row.data["status"]
        if body["verdict"]=="publish":
            if current!="candidate": raise DomainError("workflow_transition_forbidden",409,"Seule une release candidate peut être publiée.")
            data=update_row(row,status="published")
            event="knowledge.published"
        else:
            if current!="published": raise DomainError("workflow_transition_forbidden",409,"Seule une release publiée peut être révoquée.")
            data=update_row(row,status="revoked")
            event="knowledge.revoked"
            affected=[]
            evaluations=db.execute(select(Entity).where(Entity.tenant_id==ctx.tenant_id,Entity.kind=="Evaluation")).scalars().all()
            for evaluation in evaluations:
                if evaluation.data.get("knowledge_release",{}).get("digest")==row.data["release_id"] and not evaluation.data.get("stale",False):
                    update_row(evaluation,stale=True)
                    affected.append(evaluation.id)
                    for proposal in db.execute(select(Entity).where(Entity.tenant_id==ctx.tenant_id,Entity.kind=="ActionProposal",Entity.parent_id==evaluation.parent_id)).scalars().all():
                        if proposal.data.get("evaluation_id")==evaluation.id and proposal.data.get("status") in {"proposed","accepted"}:
                            update_row(proposal,status="superseded")
            create_entity(db,ctx,"ImpactAnalysis",{
                "subject_kind":"KnowledgeRelease","subject_id":row.id,"source_kind":"KnowledgeRelease",
                "source_id":row.id,"reason":body["reason"],"status":"open","affected_entity_ids":affected,
                "created_by_event":"knowledge.revoked",
            },status="open")
        emit_event(db,ctx,event,"KnowledgeRelease",row.id,row.revision,correlation(request),{"release_id":row.data["release_id"],"reason":body["reason"]})
        operation=make_operation(db,ctx,"decide_release",row.id,correlation(request)); return operation,202,str(operation["revision"])
    p,s,e=idempotent(db,ctx,"decideRelease",idempotency_key,body,action); return response(p,s,e)


@router.post("/knowledge/activations")
def activate_release(request:Request, body:dict=Body(...), idempotency_key:str|None=Header(None,alias="Idempotency-Key"), db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"activateRelease"); validate("ReleaseActivation",body); _require_engineering_policy(body["policy_ref"])
    def action():
        ref=body["release_ref"]
        row=_release_row_by_digest(db,ctx,ref["digest"])
        if row is None: raise DomainError("not_found",404,"Release introuvable.")
        expected=_release_ref_for_row(row)
        if not _same_artifact_ref(ref,expected): raise DomainError("artifact_integrity_failed",422,"Référence de release incohérente.")
        if row.data["status"]!="published": raise DomainError("release_not_admitted",409,"Seule une release publiée peut être activée.")
        if row.data.get("synthetic") and row.data.get("usage")!="engineering": raise DomainError("clinical_use_not_admitted",403,"Une release synthétique ne peut être admise cliniquement.")
        cfg,rev=get_configuration(db,ctx,settings.configuration_default)
        cfg["local_release_ref"]=ref
        state=db.get(ConfigurationState,ctx.tenant_id); state.data=cfg; state.revision+=1; state.updated_at=utcnow()
        audit(db,ctx,"knowledge.activated",correlation(request),target_kind="KnowledgeRelease",target_id=row.id,detail={"reason":body["reason"]})
        emit_event(db,ctx,"knowledge.activated","KnowledgeRelease",row.id,row.revision,correlation(request),{"release_id":row.data["release_id"],"reason":body["reason"]})
        operation=make_operation(db,ctx,"activate_release",row.id,correlation(request)); return operation,202,str(operation["revision"])
    p,s,e=idempotent(db,ctx,"activateRelease",idempotency_key,body,action); return response(p,s,e)


@router.post("/knowledge/exports")
def export_knowledge(request:Request, body:dict=Body(...), idempotency_key:str|None=Header(None,alias="Idempotency-Key"), db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"exportKnowledge"); validate("ExportRequest",body); _require_engineering_policy(body["policy_ref"])
    def action():
        ref=body["release_ref"]
        if _same_artifact_ref(ref,syn.SYN_RELEASE):
            release_ok=True
        else:
            release=_release_row_by_digest(db,ctx,ref["digest"])
            release_ok=release is not None and _same_artifact_ref(ref,_release_ref_for_row(release)) and release.data.get("status")=="published"
        if not release_ok:
            raise DomainError("release_not_admitted",409,"Release absente, incohérente ou non publiée.")
        # Les profils externes Kristal/FHIR ne sont pas fournis dans ce dépôt. Ne jamais simuler un export réussi.
        operation=make_operation(db,ctx,"export_knowledge",None,correlation(request),status="failed",error_code="capability_unavailable")
        audit(db,ctx,"knowledge.export_blocked",correlation(request),detail={"target":body["target"],"release":body["release_ref"],"reason":"connector_profile_not_configured"})
        return operation,202,str(operation["revision"])
    p,s,e=idempotent(db,ctx,"exportKnowledge",idempotency_key,body,action); return response(p,s,e)


@router.post("/contributions")
def submit_contribution(request:Request, body:dict=Body(...), idempotency_key:str|None=Header(None,alias="Idempotency-Key"), db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"submitContribution"); validate("ContributionInput",body)
    def action():
        item=create_entity(db,ctx,"Contribution",{**body,"status":"submitted"},status="submitted")
        emit_event(db,ctx,"contribution.updated","Contribution",item["id"],item["revision"],correlation(request),{"status":"submitted"})
        return item,201,str(item["revision"])
    p,s,e=idempotent(db,ctx,"submitContribution",idempotency_key,body,action); return response(p,s,e)


@router.get("/contributions")
def list_contributions(cursor:str|None=Query(None), limit:int=Query(50,ge=1,le=100), db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"listContributions"); return page(list_entities(db,ctx,"Contribution"),ctx=ctx,route="listContributions",cursor=cursor,limit=limit)


@router.get("/contributions/{contribution_id}")
def get_contribution(contribution_id:str, db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"getContribution"); item=get_entity(db,ctx,"Contribution",contribution_id); return response(item,etag=str(item["revision"]))


@router.post("/contributions/{contribution_id}/reviews")
def review_contribution(contribution_id:str, request:Request, body:dict=Body(...), idempotency_key:str|None=Header(None,alias="Idempotency-Key"), if_match:str|None=Header(None,alias="If-Match"), db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"reviewContribution"); validate("ReviewDecision",body)
    def action():
        row=get_row(db,ctx,"Contribution",contribution_id,for_update=True); enforce_match(row,if_match)
        if row.data["status"] not in {"submitted","screening","under_review","changes_requested"}: raise DomainError("workflow_transition_forbidden",409,"Contribution non révisable dans cet état.")
        status={"accept":"accepted","reject":"rejected","request_changes":"changes_requested"}[body["verdict"]]
        item=update_row(row,status=status)
        emit_event(db,ctx,"contribution.updated","Contribution",row.id,item["revision"],correlation(request),{"status":status})
        return item,200,str(item["revision"])
    p,s,e=idempotent(db,ctx,"reviewContribution",idempotency_key,body,action); return response(p,s,e)


@router.post("/providers/policies")
def set_provider_policy(request:Request, body:dict=Body(...), idempotency_key:str|None=Header(None,alias="Idempotency-Key"), db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"setProviderPolicy"); validate("ProviderPolicyInput",body)
    cfg,_=get_configuration(db,ctx,settings.configuration_default)
    if _ts(body["period_start"]) >= _ts(body["period_end"]):
        raise DomainError("invalid_request",422,"period_end doit être postérieur à period_start.")
    if body["enabled"] and cfg["mode"]!="online_extended":
        raise DomainError("unsupported_profile",422,"Un fournisseur payant ne peut être activé hors online_extended.")
    if body["enabled"] and body["currency"] != cfg.get("currency"):
        raise DomainError("unsupported_profile",422,"La devise fournisseur doit correspondre à la devise configurée.")
    def action():
        previous=db.execute(select(Entity).where(
            Entity.tenant_id==ctx.tenant_id,Entity.kind=="ProviderPolicy",Entity.foreign_key==body["provider_id"]
        ).order_by(Entity.created_at.desc()).with_for_update()).scalars().first()
        reserved=spent=0
        if previous is not None:
            old=previous.data
            same_period=(old.get("period_start")==body["period_start"] and old.get("period_end")==body["period_end"] and old.get("currency")==body["currency"])
            if not same_period and int(old.get("_reserved_minor",0))>0:
                raise DomainError("provider_outcome_unknown",409,"Une réserve fournisseur doit être réconciliée avant de changer de période ou devise.")
            if same_period:
                reserved=int(old.get("_reserved_minor",0)); spent=int(old.get("_spent_minor",0))
        stored={**body,"_reserved_minor":reserved,"_spent_minor":spent}
        item=create_entity(db,ctx,"ProviderPolicy",stored,foreign_key=body["provider_id"])
        emit_event(db,ctx,"provider.policy_changed","ProviderPolicy",item["id"],item["revision"],correlation(request),{"provider_id":body["provider_id"],"enabled":body["enabled"]})
        public={k:v for k,v in item.items() if not k.startswith("_")}
        return public,201,str(item["revision"])
    p,s,e=idempotent(db,ctx,"setProviderPolicy",idempotency_key,body,action); return response(p,s,e)


@router.get("/providers/{provider_id}/usage")
def get_provider_usage(provider_id:str, db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"getProviderUsage")
    policies=[x for x in list_entities(db,ctx,"ProviderPolicy") if x["provider_id"]==provider_id]
    if not policies: raise DomainError("not_found",404,"Politique fournisseur introuvable.")
    p=policies[-1]
    return {"provider_id":provider_id,"period_start":p["period_start"],"period_end":p["period_end"],"reserved_minor":int(p.get("_reserved_minor",0)),"spent_minor":int(p.get("_spent_minor",0)),"currency":p["currency"]}


@router.get("/operations/{operation_id}")
def get_operation(operation_id:str, db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"getOperation"); item=get_entity(db,ctx,"Operation",operation_id); return response(item,etag=str(item["revision"]))


@router.post("/cases/{case_id}/treatment-evaluations")
def evaluate_treatments(case_id:str, request:Request, body:dict=Body(...), idempotency_key:str|None=Header(None,alias="Idempotency-Key"), if_match:str|None=Header(None,alias="If-Match"), db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"evaluateTreatments"); validate("TreatmentRequest",body)
    def action():
        case=get_row(db,ctx,"ClinicalCase",case_id,for_update=True); enforce_match(case,if_match); require_case_revision(case,body["case_revision"])
        evaluation=get_row(db,ctx,"Evaluation",body["evaluation_id"])
        if evaluation.parent_id != case_id or evaluation.data.get("stale"):
            raise DomainError("stale_case",409,"L'évaluation est périmée ou étrangère au cas.")
        for protocol_ref in body["protocol_refs"]:
            _require_known_ref(protocol_ref, syn.protocols(), "protocole")
        allergies=[o for o in list_entities(db,ctx,"Observation",parent_id=case_id) if o["kind"]=="allergy" and o["status"]!="entered_in_error"]
        allergy_known=any(o["presence"] in {"present","absent"} for o in allergies)
        option=create_entity(db,ctx,"TreatmentOption",syn.treatment_option(case.data,allergy_known),parent_id=case_id,status="proposed" if allergy_known else "needs_information")
        emit_event(db,ctx,"treatment.evaluated","TreatmentOption",option["id"],option["revision"],correlation(request),{"case_id":case_id,"status":option["status"]})
        operation=make_operation(db,ctx,"evaluate_treatments",option["id"],correlation(request)); return operation,202,str(operation["revision"])
    p,s,e=idempotent(db,ctx,"evaluateTreatments",idempotency_key,body,action); return response(p,s,e)


@router.get("/cases/{case_id}/treatment-options")
def list_treatment_options(case_id:str, cursor:str|None=Query(None), limit:int=Query(50,ge=1,le=100), db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"listTreatmentOptions"); get_row(db,ctx,"ClinicalCase",case_id); return page(list_entities(db,ctx,"TreatmentOption",parent_id=case_id),ctx=ctx,route="listTreatmentOptions",cursor=cursor,limit=limit,scope={"case_id":case_id})


@router.get("/configuration")
def get_configuration_api(db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"getConfiguration"); cfg,rev=get_configuration(db,ctx,settings.configuration_default); return response(cfg,etag=str(rev))


@router.post("/configuration/changes")
def change_configuration(request:Request, body:dict=Body(...), idempotency_key:str|None=Header(None,alias="Idempotency-Key"), if_match:str|None=Header(None,alias="If-Match"), db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"changeConfiguration"); validate("Configuration",body)
    def action():
        current,rev=get_configuration(db,ctx,settings.configuration_default)
        expected=expected_revision(if_match)
        if expected!=rev: raise DomainError("precondition_failed",412,"La configuration a changé.")
        if body.get("local_release_ref") != current.get("local_release_ref"):
            raise DomainError("workflow_transition_forbidden",409,"Utiliser /knowledge/activations pour changer la release locale active.")
        if body["mode"]=="offline_free" and body["network_scope"]=="internet": raise DomainError("unsupported_profile",422,"offline_free interdit le WAN.")
        if body["mode"] in {"offline_free","online_free"} and body["paid_budget_minor"]!=0: raise DomainError("unsupported_profile",422,"Ce mode interdit un budget payant.")
        if body["intended_use"]=="clinical_execution" and body["execution_policy"]!="protocol_authorized": raise DomainError("clinical_use_not_admitted",422,"clinical_execution exige une politique d'exécution admise.")
        state=db.get(ConfigurationState,ctx.tenant_id); state.data=body; state.revision+=1; state.updated_at=utcnow()
        audit(db,ctx,"configuration.changed",correlation(request),detail={"from":current["mode"],"to":body["mode"]})
        emit_event(db,ctx,"configuration.changed","Configuration",ctx.tenant_id,state.revision,correlation(request),{"from":current["mode"],"to":body["mode"]})
        return body,200,str(state.revision)
    p,s,e=idempotent(db,ctx,"changeConfiguration",idempotency_key,body,action); return response(p,s,e)


# Versioned catalogs: sites, managed resources, procedure catalog.
def _register_catalog_routes() -> None:
    specs = [
        ("/sites", "Site", "SiteInput", "SiteRevision", "listSite", "createSite", "getSite", "reviseSite"),
        ("/managed-resources", "ManagedResource", "ManagedResourceInput", "ManagedResourceRevision", "listManagedResource", "createManagedResource", "getManagedResource", "reviseManagedResource"),
        ("/procedure-catalog", "ProcedureEntry", "ProcedureEntryInput", "ProcedureEntryRevision", "listProcedureEntry", "createProcedureEntry", "getProcedureEntry", "reviseProcedureEntry"),
    ]

    def make_handlers(spec: tuple[str, str, str, str, str, str, str, str]):
        path, kind, input_schema, revision_schema, list_op, create_op, get_op, revise_op = spec

        # Keep routing metadata in the closure, never as default-valued FastAPI parameters:
        # otherwise a client could override ``kind``/``operation`` through query strings.
        def list_handler(request: Request, db: Session = Depends(get_session), ctx: AuthContext = Depends(auth_context)):
            op(ctx, list_op)
            raw_limit = request.query_params.get("limit")
            try:
                limit = 50 if raw_limit is None else int(raw_limit)
            except ValueError as exc:
                raise DomainError("invalid_request", 422, "limit doit être un entier entre 1 et 100.") from exc
            if not 1 <= limit <= 100:
                raise DomainError("invalid_request", 422, "limit doit être compris entre 1 et 100.")
            cursor = request.query_params.get("cursor")
            if cursor == "":
                raise DomainError("invalid_request", 422, "cursor ne peut pas être vide.")
            site_id = request.query_params.get("site_id") if kind == "ManagedResource" else None
            q = request.query_params.get("q") if kind == "ProcedureEntry" else None
            family = request.query_params.get("family") if kind == "ProcedureEntry" else None
            items = list_entities(db, ctx, kind)
            if kind == "ManagedResource" and site_id:
                items = [x for x in items if x.get("site_id") == site_id]
            if kind == "ProcedureEntry" and family:
                items = [x for x in items if x.get("family") == family]
            if kind == "ProcedureEntry" and q:
                items = [x for x in items if q.lower() in x.get("concept", {}).get("code", "").lower()]
            scope = {"site_id": site_id, "q": q, "family": family}
            return page(items, ctx=ctx, route=list_op, cursor=cursor, limit=limit, scope=scope)

        def create_handler(request: Request, body: dict = Body(...), idempotency_key: str | None = Header(None, alias="Idempotency-Key"), db: Session = Depends(get_session), ctx: AuthContext = Depends(auth_context)):
            op(ctx, create_op)

            def action():
                if kind == "ManagedResource":
                    get_row(db, ctx, "Site", body["site_id"])
                item = catalog_create(kind, input_schema, body, db, ctx)
                emit_event(db,ctx,"catalog.changed",kind,item["id"],item["revision"],correlation(request),{"reason":"created"})
                return item, 201, str(item["revision"])

            p, status, etag = idempotent(db, ctx, create_op, idempotency_key, body, action)
            return response(p, status, etag)

        def get_handler(item_id: str, db: Session = Depends(get_session), ctx: AuthContext = Depends(auth_context)):
            op(ctx, get_op)
            item = get_entity(db, ctx, kind, item_id)
            return response(item, etag=str(item["revision"]))

        def revise_handler(item_id: str, request: Request, body: dict = Body(...), idempotency_key: str | None = Header(None, alias="Idempotency-Key"), if_match: str | None = Header(None, alias="If-Match"), db: Session = Depends(get_session), ctx: AuthContext = Depends(auth_context)):
            op(ctx, revise_op)

            def action():
                previous = get_row(db, ctx, kind, item_id)
                previous_status = previous.data.get("status")
                item = catalog_revise(kind, revision_schema, item_id, body, if_match, db, ctx)
                if kind == "ManagedResource" and previous_status == "active" and item.get("status") in {"unavailable", "retired"}:
                    resource = get_row(db, ctx, "ManagedResource", item_id)
                    _record_resource_impacts(db, ctx, resource, correlation(request), body["reason"])
                emit_event(db, ctx, "catalog.changed", kind, item_id, item["revision"], correlation(request), {"reason": body["reason"]})
                return item, 200, str(item["revision"])

            p, status, etag = idempotent(db, ctx, revise_op, idempotency_key, body, action)
            return response(p, status, etag)

        return path, list_handler, create_handler, get_handler, revise_handler, list_op, create_op, get_op, revise_op

    for spec in specs:
        path, list_handler, create_handler, get_handler, revise_handler, list_op, create_op, get_op, revise_op = make_handlers(spec)
        router.add_api_route(path, list_handler, methods=["GET"], name=list_op)
        router.add_api_route(path, create_handler, methods=["POST"], name=create_op)
        router.add_api_route(path + "/{item_id}", get_handler, methods=["GET"], name=get_op)
        router.add_api_route(path + "/{item_id}/revisions", revise_handler, methods=["POST"], name=revise_op)


_register_catalog_routes()


@router.post("/workflows")
def create_workflow(request:Request, body:dict=Body(...), idempotency_key:str|None=Header(None,alias="Idempotency-Key"), db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"createWorkflow"); validate("WorkflowInput",body)
    def action():
        case=get_row(db,ctx,"ClinicalCase",body["case_id"]); require_case_revision(case,body["case_revision"])
        _require_known_ref(body["protocol_ref"], syn.protocols(), "protocole")
        if not _same_artifact_ref(body["authorization_policy_ref"], syn.AUTH_POLICY):
            raise DomainError("clinical_use_not_admitted",403,"Politique d'autorisation inconnue ou non admise.")
        if body["intended_use"] != case.data.get("intended_use"):
            raise DomainError("authorization_scope_mismatch",403,"La finalité du workflow doit correspondre à celle du cas.")
        status="ready"
        reasons=[]
        item=create_entity(db,ctx,"WorkflowRun",{**body,"status":status,"current_step_ids":["evaluate"],"reason_codes":reasons},parent_id=case.id,status=status)
        emit_event(db,ctx,"workflow.changed","WorkflowRun",item["id"],item["revision"],correlation(request),{"status":status,"reason":"created"})
        return item,201,str(item["revision"])
    p,s,e=idempotent(db,ctx,"createWorkflow",idempotency_key,body,action); return response(p,s,e)


@router.get("/workflows/{workflow_id}")
def get_workflow(workflow_id:str, db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"getWorkflow"); item=get_entity(db,ctx,"WorkflowRun",workflow_id); return response(item,etag=str(item["revision"]))


@router.post("/workflows/{workflow_id}/transitions")
def transition_workflow(workflow_id:str, request:Request, body:dict=Body(...), idempotency_key:str|None=Header(None,alias="Idempotency-Key"), if_match:str|None=Header(None,alias="If-Match"), db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"transitionWorkflow"); validate("WorkflowTransition",body)
    mapping={"start":{"ready":"running"},"pause":{"running":"paused","waiting_input":"paused","waiting_review":"paused","waiting_external":"paused","reconciling":"paused"},"resume":{"paused":"running","waiting_review":"running"},"cancel":{"ready":"cancelled","running":"cancelled","waiting_input":"cancelled","waiting_review":"cancelled","waiting_external":"cancelled","reconciling":"cancelled","paused":"cancelled"}}
    def action():
        row=get_row(db,ctx,"WorkflowRun",workflow_id,for_update=True); enforce_match(row,if_match)
        case=get_row(db,ctx,"ClinicalCase",row.parent_id); require_case_revision(case,body["case_revision"])
        nxt=mapping.get(body["action"],{}).get(row.data["status"])
        if not nxt: raise DomainError("workflow_transition_forbidden",409,"Transition workflow interdite.")
        item=update_row(row,status=nxt,case_revision=case.revision,reason_codes=[])
        emit_event(db,ctx,"workflow.changed","WorkflowRun",workflow_id,item["revision"],correlation(request),{"status":nxt,"reason":body["reason"]})
        return item,200,str(item["revision"])
    p,s,e=idempotent(db,ctx,"transitionWorkflow",idempotency_key,body,action); return response(p,s,e)


@router.get("/cases/{case_id}/workflows")
def list_case_workflows(case_id:str, cursor:str|None=Query(None), limit:int=Query(50,ge=1,le=100), db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"listCaseWorkflows"); get_row(db,ctx,"ClinicalCase",case_id); return page(list_entities(db,ctx,"WorkflowRun",parent_id=case_id),ctx=ctx,route="listCaseWorkflows",cursor=cursor,limit=limit,scope={"case_id":case_id})


@router.post("/cases/{case_id}/result-batches")
def receive_result_batch(case_id:str, request:Request, body:dict=Body(...), idempotency_key:str|None=Header(None,alias="Idempotency-Key"), if_match:str|None=Header(None,alias="If-Match"), db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"receiveResultBatch"); validate("ResultBatchInput",body)
    def action():
        # Authorize the case and require a syntactically valid precondition even for a
        # transport replay. An exact already-accepted external report is then safe to
        # return without requiring the case to still be at its historical revision.
        get_row(db,ctx,"ClinicalCase",case_id)
        expected_revision(if_match)
        canonical={k:body[k] for k in ("owner","report_id","report_version","items")}
        calculated=digest(canonical)
        if body["digest"]!=calculated: raise DomainError("artifact_integrity_failed",422,"Le digest du rapport ne correspond pas à sa représentation canonique.")
        ext=db.execute(select(ExternalVersion).where(ExternalVersion.tenant_id==ctx.tenant_id,ExternalVersion.namespace==f"result-report:{body['owner']}",ExternalVersion.foreign_id==body["report_id"],ExternalVersion.foreign_version==body["report_version"])).scalar_one_or_none()
        if ext:
            if ext.digest!=body["digest"]: raise DomainError("source_version_conflict",409,"Même version de rapport avec contenu divergent.")
            receipt_row=get_row(db,ctx,"ResultReceipt",ext.entity_id)
            if receipt_row.parent_id!=case_id:
                raise DomainError("source_version_conflict",409,"Cette identité/version de rapport est déjà liée à un autre cas.")
            receipt=dict(receipt_row.data); return receipt,200,str(receipt["revision"])
        case=get_row(db,ctx,"ClinicalCase",case_id,for_update=True); enforce_match(case,if_match); require_case_revision(case,body["case_revision"])
        observations=[]
        # Validate all links first, then persist atomically.
        replacement_ids=[item.get("replaces_id") for item in body["items"] if item.get("replaces_id")]
        if len(replacement_ids)!=len(set(replacement_ids)):
            raise DomainError("invalid_request",422,"Un même résultat existant ne peut être remplacé deux fois dans le même lot.")
        external_item_ids=[item["external_item_id"] for item in body["items"]]
        if len(external_item_ids)!=len(set(external_item_ids)):
            raise DomainError("source_version_conflict",409,"external_item_id dupliqué dans le lot.")
        for item in body["items"]:
            if item.get("replaces_id"):
                replaced=get_row(db,ctx,"Observation",item["replaces_id"])
                if replaced.parent_id!=case_id:
                    raise DomainError("authorization_scope_mismatch",403,"Le résultat remplacé appartient à un autre cas.")
            validate("RecordObservation",item["observation"])
        for item in body["items"]:
            obs=create_entity(db,ctx,"Observation",{"case_id":case_id,"recorded_at":now_iso(),"replaces_id":item.get("replaces_id"),**item["observation"]},parent_id=case_id,status=item["observation"]["status"])
            observations.append(obs["id"])
            if item.get("replaces_id"):
                old=get_row(db,ctx,"Observation",item["replaces_id"],for_update=True); update_row(old,status="amended")
        case_data=update_row(case)
        stale_case_dependents(db,ctx,case_id,case_data["revision"])
        receipt=create_entity(db,ctx,"ResultReceipt",{"case_id":case_id,"case_revision":case_data["revision"],"owner":body["owner"],"report_id":body["report_id"],"report_version":body["report_version"],"digest":body["digest"],"status":"accepted","observation_ids":observations,"reason_codes":[]},parent_id=case_id,status="accepted")
        db.add(ExternalVersion(id=uuid4(),tenant_id=ctx.tenant_id,namespace=f"result-report:{body['owner']}",foreign_id=body["report_id"],foreign_version=body["report_version"],digest=body["digest"],entity_id=receipt["id"],created_at=utcnow()))
        emit_event(db,ctx,"results.accepted","ResultReceipt",receipt["id"],receipt["revision"],correlation(request),{"case_id":case_id,"receipt_id":receipt["id"]})
        if case_data["lifecycle"]=="closed":
            # Reference policy: the authenticated principal that accepted a late result
            # owns the durable follow-up until an explicit reassignment.  This avoids
            # creating an apparently monitored task with no responsible party.
            followup=create_entity(db,ctx,"FollowUpTask",{
                "case_id":case_id,"origin_ref":f"result-receipt:{receipt['id']}",
                "owner_ref":ctx.principal_id,"due_at":now_iso(),
                "reason":"Résultat reçu après clôture; suivi assigné au principal ayant accepté le lot.",
                "status":"assigned","completion_ref":None,
            },parent_id=case_id,status="assigned")
            emit_event(db,ctx,"followup.changed","FollowUpTask",followup["id"],followup["revision"],correlation(request),{
                "status":"assigned","owner_ref":ctx.principal_id,"reason":"late_result_after_case_close",
            })
        return receipt,200,str(receipt["revision"])
    p,s,e=idempotent(db,ctx,"receiveResultBatch",idempotency_key,body,action); return response(p,s,e)


@router.post("/followups")
def create_followup(request:Request, body:dict=Body(...), idempotency_key:str|None=Header(None,alias="Idempotency-Key"), db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"createFollowUp"); validate("FollowUpInput",body)
    def action():
        get_row(db,ctx,"ClinicalCase",body["case_id"])
        status="assigned" if body.get("owner_ref") else "open"
        item=create_entity(db,ctx,"FollowUpTask",{**body,"status":status,"completion_ref":None},parent_id=body["case_id"],status=status)
        emit_event(db,ctx,"followup.changed","FollowUpTask",item["id"],item["revision"],correlation(request),{"status":status})
        return item,201,str(item["revision"])
    p,s,e=idempotent(db,ctx,"createFollowUp",idempotency_key,body,action); return response(p,s,e)


@router.get("/followups/{task_id}")
def get_followup(task_id:str, db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"getFollowUp"); item=get_entity(db,ctx,"FollowUpTask",task_id); return response(item,etag=str(item["revision"]))


@router.post("/followups/{task_id}/transitions")
def transition_followup(task_id:str, request:Request, body:dict=Body(...), idempotency_key:str|None=Header(None,alias="Idempotency-Key"), if_match:str|None=Header(None,alias="If-Match"), db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"transitionFollowUp"); validate("FollowUpTransition",body)
    allowed={"open":{"assigned","cancelled"},"assigned":{"open","completed","cancelled"},"completed":set(),"cancelled":set()}
    def action():
        row=get_row(db,ctx,"FollowUpTask",task_id,for_update=True); enforce_match(row,if_match)
        target=body["target"]
        if target not in allowed.get(row.data["status"],set()): raise DomainError("workflow_transition_forbidden",409,"Transition de suivi interdite.")
        if target=="assigned" and not body.get("owner_ref"): raise DomainError("followup_owner_missing",422,"Un responsable est requis.")
        if target=="completed" and not body.get("completion_ref"): raise DomainError("invalid_request",422,"Une preuve ou raison de complétion est requise.")
        item=update_row(row,status=target,owner_ref=body.get("owner_ref") if target=="assigned" else row.data.get("owner_ref"),completion_ref=body.get("completion_ref") if target=="completed" else row.data.get("completion_ref"))
        emit_event(db,ctx,"followup.changed","FollowUpTask",task_id,item["revision"],correlation(request),{"status":target,"reason":body["reason"]})
        return item,200,str(item["revision"])
    p,s,e=idempotent(db,ctx,"transitionFollowUp",idempotency_key,body,action); return response(p,s,e)


@router.get("/cases/{case_id}/followups")
def list_case_followups(case_id:str, cursor:str|None=Query(None), limit:int=Query(50,ge=1,le=100), db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"listCaseFollowUps"); get_row(db,ctx,"ClinicalCase",case_id); return page(list_entities(db,ctx,"FollowUpTask",parent_id=case_id),ctx=ctx,route="listCaseFollowUps",cursor=cursor,limit=limit,scope={"case_id":case_id})


@router.post("/cases/{case_id}/care-plans")
def create_care_plan(case_id:str, request:Request, body:dict=Body(...), idempotency_key:str|None=Header(None,alias="Idempotency-Key"), if_match:str|None=Header(None,alias="If-Match"), db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"createCarePlan"); validate("CarePlanInput",body)
    def action():
        case=get_row(db,ctx,"ClinicalCase",case_id,for_update=True); enforce_match(case,if_match); require_case_revision(case,body["case_revision"])
        for oid in body["treatment_option_ids"]:
            o=get_row(db,ctx,"TreatmentOption",oid)
            if o.parent_id!=case_id: raise DomainError("authorization_scope_mismatch",403,"Option hors du cas.")
        for tid in body["followup_task_ids"]:
            t=get_row(db,ctx,"FollowUpTask",tid)
            if t.parent_id!=case_id: raise DomainError("authorization_scope_mismatch",403,"Suivi hors du cas.")
        item=create_entity(db,ctx,"CarePlan",{**body,"case_id":case_id,"status":"active"},parent_id=case_id,status="active")
        emit_event(db,ctx,"care_plan.changed","CarePlan",item["id"],item["revision"],correlation(request),{"status":"active"})
        return item,200,str(item["revision"])
    p,s,e=idempotent(db,ctx,"createCarePlan",idempotency_key,body,action); return response(p,s,e)


@router.get("/cases/{case_id}/care-plans")
def list_case_care_plans(case_id:str, cursor:str|None=Query(None), limit:int=Query(50,ge=1,le=100), db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"listCaseCarePlans"); get_row(db,ctx,"ClinicalCase",case_id); return page(list_entities(db,ctx,"CarePlan",parent_id=case_id),ctx=ctx,route="listCaseCarePlans",cursor=cursor,limit=limit,scope={"case_id":case_id})


@router.get("/care-plans/{plan_id}")
def get_care_plan(plan_id:str, db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"getCarePlan"); item=get_entity(db,ctx,"CarePlan",plan_id); return response(item,etag=str(item["revision"]))


@router.post("/care-plans/{plan_id}/revisions")
def revise_care_plan(plan_id:str, request:Request, body:dict=Body(...), idempotency_key:str|None=Header(None,alias="Idempotency-Key"), if_match:str|None=Header(None,alias="If-Match"), db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"reviseCarePlan"); validate("CarePlanRevision",body)
    def action():
        row=get_row(db,ctx,"CarePlan",plan_id,for_update=True); enforce_match(row,if_match)
        case=get_row(db,ctx,"ClinicalCase",row.parent_id); require_case_revision(case,body["replacement"]["case_revision"])
        for oid in body["replacement"]["treatment_option_ids"]:
            option=get_row(db,ctx,"TreatmentOption",oid)
            if option.parent_id!=case.id: raise DomainError("authorization_scope_mismatch",403,"Option hors du cas.")
        for tid in body["replacement"]["followup_task_ids"]:
            task=get_row(db,ctx,"FollowUpTask",tid)
            if task.parent_id!=case.id: raise DomainError("authorization_scope_mismatch",403,"Suivi hors du cas.")
        item=update_row(row,replacement={**body["replacement"],"case_id":case.id,"status":body["status"]})
        emit_event(db,ctx,"care_plan.changed","CarePlan",plan_id,item["revision"],correlation(request),{"status":body["status"],"reason":body["reason"]})
        return item,200,str(item["revision"])
    p,s,e=idempotent(db,ctx,"reviseCarePlan",idempotency_key,body,action); return response(p,s,e)
