from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from fastapi import APIRouter, Body, Depends, Header, Query, Request
from fastapi.responses import ORJSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import synthetic as syn
from .config import load_settings
from .contracts import validate
from .db import ConfigurationState, Entity, ExternalVersion, get_session, utcnow
from .errors import DomainError
from .security import AuthContext, auth_context, authorize
from .store import (
    audit,
    create_entity,
    emit_event,
    enforce_match,
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


def page(items: list[dict]) -> dict:
    return {"items": items, "next_cursor": None}


def response(payload: dict, status_code: int = 200, etag: str | None = None) -> ORJSONResponse:
    headers = {"ETag": f'"{etag}"'} if etag is not None else None
    return ORJSONResponse(payload, status_code=status_code, headers=headers)


def op(ctx: AuthContext, operation_id: str) -> None:
    authorize(ctx, operation_id)


def correlation(request: Request) -> str:
    return request.state.correlation_id


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
    return create_entity(db, ctx, "Operation", {
        "kind": kind, "status": status, "result_ref": result_ref, "error_code": error_code, "correlation_id": corr,
    }, status=status)


def catalog_create(kind: str, schema: str, payload: dict, db: Session, ctx: AuthContext) -> dict:
    validate(schema, payload)
    if kind == "ProcedureEntry" and payload.get("concept") in payload.get("component_refs", []):
        raise DomainError("invalid_request", 422, "Un acte ne peut pas se contenir lui-même comme composant.")
    parent_id = payload.get("site_id") if kind == "ManagedResource" else None
    return create_entity(db, ctx, kind, payload, parent_id=parent_id, status=payload.get("status"))


def catalog_revise(kind: str, schema: str, item_id: str, body: dict, if_match: str | None, db: Session, ctx: AuthContext) -> dict:
    validate(schema, body)
    row = get_row(db, ctx, kind, item_id, for_update=True)
    enforce_match(row, if_match)
    replacement = body["replacement"]
    if kind == "ProcedureEntry" and replacement.get("concept") in replacement.get("component_refs", []):
        raise DomainError("invalid_request", 422, "Un acte ne peut pas se contenir lui-même comme composant.")
    if kind == "ManagedResource" and replacement.get("site_id") != row.data.get("site_id"):
        # site may change, but it must still exist in the tenant
        get_row(db, ctx, "Site", replacement["site_id"])
    updated = update_row(row, replacement=replacement)
    row.parent_id = replacement.get("site_id") if kind == "ManagedResource" else row.parent_id
    return updated


@router.get("/capabilities")
def get_capabilities(request: Request, db: Session = Depends(get_session), ctx: AuthContext = Depends(auth_context)):
    op(ctx, "getCapabilities")
    cfg, _ = get_configuration(db, ctx, settings.configuration_default)
    network = cfg["network_scope"]
    paid = cfg["mode"] == "online_extended"
    core = [
        ("cases", "implemented", False, False), ("observations", "implemented", False, False),
        ("synthetic_inference", "implemented", False, False), ("workflows", "implemented", False, False),
        ("planning", "implemented", False, False), ("resources", "implemented", False, False),
        ("treatment_options", "implemented", False, False), ("followup", "implemented", False, False),
        ("knowledge_registry", "implemented", False, False), ("contributions", "implemented", False, False),
        ("provider_network", "implemented" if network == "internet" else "unavailable", True, True),
        ("fhir_partner", "unavailable", True, False), ("kristal_export", "implemented", False, False),
    ]
    caps = [{"name": n, "state": s, "requires_network": rn, "paid": p, "supported_uses": ["engineering"], "limitations": (["Données et modèles cliniques réels non livrés."] if n != "provider_network" else ["Aucun fournisseur activé implicitement."])} for n, s, rn, p in core]
    return {"api_version": "0.2.0", "mode": cfg["mode"], "network_scope": cfg["network_scope"], "capabilities": caps}


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
def list_cases(db: Session = Depends(get_session), ctx: AuthContext = Depends(auth_context)):
    op(ctx, "listCases"); return page(list_entities(db, ctx, "ClinicalCase"))


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
def list_observations(case_id: str, db: Session = Depends(get_session), ctx: AuthContext = Depends(auth_context)):
    op(ctx, "listObservations"); get_row(db, ctx, "ClinicalCase", case_id); return page(list_entities(db, ctx, "Observation", parent_id=case_id))


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
def list_proposals(case_id: str, db: Session = Depends(get_session), ctx: AuthContext = Depends(auth_context)):
    op(ctx, "listProposals"); get_row(db, ctx, "ClinicalCase", case_id); return page(list_entities(db, ctx, "ActionProposal", parent_id=case_id))


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
        return item, 200, str(item["revision"])
    payload, status, etag = idempotent(db, ctx, "decideProposal", idempotency_key, body, action)
    return response(payload, status, etag)


@router.post("/plans")
def compare_plans(request: Request, body: dict = Body(...), idempotency_key: str | None = Header(None, alias="Idempotency-Key"), db: Session = Depends(get_session), ctx: AuthContext = Depends(auth_context)):
    op(ctx, "comparePlans"); validate("PlanRequest", body)
    def action():
        case = get_row(db, ctx, "ClinicalCase", body["case_id"]); require_case_revision(case, body["case_revision"])
        evaluation = get_row(db, ctx, "Evaluation", body["evaluation_id"])
        if evaluation.parent_id != case.id or evaluation.data.get("stale"): raise DomainError("stale_case", 409, "Évaluation périmée ou étrangère au cas.")
        comparisons = []
        strategies = []
        cost_refs = []
        for proposal_id in body["proposal_ids"]:
            p = get_row(db, ctx, "ActionProposal", proposal_id)
            if p.parent_id != case.id: raise DomainError("authorization_scope_mismatch", 403, "Proposition hors du cas.")
            strategy = artifact_ref(f"proposal:{proposal_id}")
            strategies.append(strategy["id"])
            criteria = []
            if p.data["kind"] == "test":
                cost = next((c for c in list_entities(db, ctx, "CostQuote") if c.get("capability_id") in body["resource_snapshot_ids"]), None)
                if cost is None:
                    criteria.append({"criterion_ref": artifact_ref("cost"), "state": "unknown", "value": None, "unit": "minor_currency_unit", "source_refs": []})
                else:
                    criteria.append({"criterion_ref": artifact_ref("cost"), "state": "known", "value": float(cost["amount_minor"]), "unit": cost["currency"], "source_refs": []})
            else:
                criteria.append({"criterion_ref": artifact_ref("resource_requirement"), "state": "known", "value": 0.0, "unit": "synthetic", "source_refs": []})
            comparisons.append({"strategy_ref": strategy, "admissible": True, "reason_codes": ["synthetic_comparison"], "criteria": criteria, "dominated_by": []})
        plan_payload = {
            "case_id": case.id, "case_revision": case.revision, "status": "feasible" if strategies else "unknown",
            "strategy_refs": strategies, "selected_strategy_ref": None,
            "limitations": ["Comparaison Pareto synthétique; aucune utilité clinique inventée."], "policy_ref": body["policy_ref"],
            "resource_snapshot_ids": body["resource_snapshot_ids"], "explanation": "Options non dominées; les critères inconnus restent inconnus.",
            "comparisons": comparisons, "cost_snapshot_refs": cost_refs, "computed_at": now_iso(),
            "valid_until": (datetime.now(timezone.utc)+timedelta(hours=1)).isoformat().replace("+00:00","Z"),
        }
        plan_item = create_entity(db, ctx, "Plan", plan_payload, parent_id=case.id, status=plan_payload["status"])
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
        if body["authorization_policy_ref"].get("id") != syn.AUTH_POLICY["id"] or case.data.get("intended_use") != "engineering":
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
def create_resource_capability(body: dict = Body(...), idempotency_key: str | None = Header(None, alias="Idempotency-Key"), db: Session = Depends(get_session), ctx: AuthContext = Depends(auth_context)):
    op(ctx, "createResourceCapability"); validate("CapabilityInput", body)
    def action():
        item = create_entity(db, ctx, "ResourceCapability", body); return item, 201, str(item["revision"])
    p,s,e=idempotent(db,ctx,"createResourceCapability",idempotency_key,body,action); return response(p,s,e)


@router.get("/resource-capabilities")
def list_resource_capabilities(db: Session = Depends(get_session), ctx: AuthContext = Depends(auth_context)):
    op(ctx, "listResourceCapabilities"); return page(list_entities(db, ctx, "ResourceCapability"))


@router.get("/resource-capabilities/{capability_id}")
def get_resource_capability(capability_id: str, db: Session = Depends(get_session), ctx: AuthContext = Depends(auth_context)):
    op(ctx,"getResourceCapability"); item=get_entity(db,ctx,"ResourceCapability",capability_id); return response(item,etag=str(item["revision"]))


@router.post("/resource-capabilities/{capability_id}/revisions")
def revise_resource_capability(capability_id: str, request: Request, body: dict=Body(...), idempotency_key: str|None=Header(None,alias="Idempotency-Key"), if_match: str|None=Header(None,alias="If-Match"), db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"reviseResourceCapability"); validate("CapabilityRevision",body)
    def action():
        row=get_row(db,ctx,"ResourceCapability",capability_id,for_update=True); enforce_match(row,if_match)
        item=update_row(row,replacement=body["replacement"])
        emit_event(db,ctx,"catalog.changed","ResourceCapability",capability_id,item["revision"],correlation(request),{"reason":body["reason"]})
        return item,200,str(item["revision"])
    p,s,e=idempotent(db,ctx,"reviseResourceCapability",idempotency_key,body,action); return response(p,s,e)


@router.post("/resource-capabilities/{capability_id}/availability")
def record_availability(capability_id: str, body: dict=Body(...), idempotency_key: str|None=Header(None,alias="Idempotency-Key"), db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"recordAvailability"); validate("AvailabilityInput",body)
    def action():
        get_row(db,ctx,"ResourceCapability",capability_id)
        for slot in body["slots"]:
            if slot["start"] >= slot["end"]: raise DomainError("invalid_request",422,"Un créneau doit avoir start < end.")
        item=create_entity(db,ctx,"AvailabilitySnapshot",{"capability_id":capability_id,**body},parent_id=capability_id)
        return item,201,str(item["revision"])
    p,s,e=idempotent(db,ctx,"recordAvailability",idempotency_key,body,action); return response(p,s,e)


@router.get("/resource-capabilities/{capability_id}/availability")
def get_availability(capability_id:str, db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"getAvailability"); get_row(db,ctx,"ResourceCapability",capability_id)
    items=list_entities(db,ctx,"AvailabilitySnapshot",parent_id=capability_id)
    if not items: raise DomainError("stale_availability",404,"Aucun snapshot de disponibilité n'est disponible.")
    item=items[-1]; return response(item,etag=str(item["revision"]))


@router.post("/cost-quotes")
def create_cost_quote(body:dict=Body(...), idempotency_key:str|None=Header(None,alias="Idempotency-Key"), db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"createCostQuote"); validate("CostInput",body)
    def action():
        get_row(db,ctx,"ResourceCapability",body["capability_id"])
        item=create_entity(db,ctx,"CostQuote",body,parent_id=body["capability_id"]); return item,201,str(item["revision"])
    p,s,e=idempotent(db,ctx,"createCostQuote",idempotency_key,body,action); return response(p,s,e)


@router.get("/cost-quotes")
def list_cost_quotes(capability_id:str|None=Query(None), db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"listCostQuotes"); items=list_entities(db,ctx,"CostQuote",parent_id=capability_id) if capability_id else list_entities(db,ctx,"CostQuote"); return page(items)


@router.post("/bookings")
def request_booking(request:Request, body:dict=Body(...), idempotency_key:str|None=Header(None,alias="Idempotency-Key"), db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"requestBooking"); validate("BookingRequest",body)
    def action():
        order=get_row(db,ctx,"ServiceOrder",body["order_id"])
        capability=get_row(db,ctx,"ResourceCapability",body["capability_id"],for_update=True)
        snap=get_row(db,ctx,"AvailabilitySnapshot",body["availability_snapshot_id"])
        if snap.parent_id!=capability.id: raise DomainError("authorization_scope_mismatch",403,"Snapshot hors de la capacité.")
        slot=next((x for x in snap.data["slots"] if x["slot_id"]==body["slot_id"]),None)
        if slot is None or slot["state"] not in {"free","held"} or slot["remaining_capacity"]<1: raise DomainError("booking_conflict",409,"Créneau non attribuable.")
        active=db.execute(select(Entity).where(Entity.tenant_id==ctx.tenant_id,Entity.kind=="Booking",Entity.foreign_key==f"{capability.id}:{body['slot_id']}",Entity.status.in_(["held","confirm_requested","confirmed","reconciling"]))).scalars().first()
        if active: raise DomainError("booking_conflict",409,"Créneau déjà réservé.")
        booking=create_entity(db,ctx,"Booking",{"order_id":order.id,"capability_id":capability.id,"slot_id":body["slot_id"],"owner":snap.data["owner"],"status":"held","hold_expires_at":snap.data["valid_until"],"foreign_ref":{"owner":snap.data["owner"],"id":f"hold-{uuid4()}","version":"1"}},parent_id=order.id,status="held",foreign_key=f"{capability.id}:{body['slot_id']}")
        operation=make_operation(db,ctx,"request_booking",booking["id"],correlation(request))
        emit_event(db,ctx,"booking.updated","Booking",booking["id"],booking["revision"],correlation(request),{"status":"held"})
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
        if row.data["status"] not in {"held","confirm_requested","reconciling"}: raise DomainError("booking_conflict",409,"Réservation non confirmable.")
        # The local synthetic facility is authoritative only for explicitly synthetic owners.
        if not row.data["owner"].startswith("synthetic"):
            item=update_row(row,status="reconciling"); operation=make_operation(db,ctx,"confirm_booking",booking_id,correlation(request),status="reconciling",error_code="provider_outcome_unknown")
        else:
            item=update_row(row,status="confirmed"); operation=make_operation(db,ctx,"confirm_booking",booking_id,correlation(request))
        emit_event(db,ctx,"booking.updated","Booking",booking_id,item["revision"],correlation(request),{"status":item["status"]})
        return operation,202,str(operation["revision"])
    p,s,e=idempotent(db,ctx,"confirmBooking",idempotency_key,body,action); return response(p,s,e)


@router.post("/bookings/{booking_id}/cancellations")
def cancel_booking(booking_id:str, request:Request, body:dict=Body(...), idempotency_key:str|None=Header(None,alias="Idempotency-Key"), if_match:str|None=Header(None,alias="If-Match"), db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"cancelBooking"); validate("ReasonCommand",body)
    def action():
        row=get_row(db,ctx,"Booking",booking_id,for_update=True); enforce_match(row,if_match)
        if row.data["status"] in {"cancelled","expired","rejected"}: raise DomainError("booking_conflict",409,"Réservation déjà terminale.")
        item=update_row(row,status="cancelled" if row.data["owner"].startswith("synthetic") else "reconciling")
        operation=make_operation(db,ctx,"cancel_booking",booking_id,correlation(request),status="succeeded" if item["status"]=="cancelled" else "reconciling",error_code=None if item["status"]=="cancelled" else "provider_outcome_unknown")
        return operation,202,str(operation["revision"])
    p,s,e=idempotent(db,ctx,"cancelBooking",idempotency_key,body,action); return response(p,s,e)


@router.post("/sources")
def register_source(body:dict=Body(...), idempotency_key:str|None=Header(None,alias="Idempotency-Key"), db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"registerSource"); validate("SourceRegistration",body)
    def action():
        item=create_entity(db,ctx,"Source",body); return item,201,str(item["revision"])
    p,s,e=idempotent(db,ctx,"registerSource",idempotency_key,body,action); return response(p,s,e)


@router.get("/sources")
def list_sources(db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"listSources"); return page(list_entities(db,ctx,"Source"))


@router.get("/sources/{source_id}")
def get_source(source_id:str, db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"getSource"); item=get_entity(db,ctx,"Source",source_id); return response(item,etag=str(item["revision"]))


@router.post("/sources/{source_id}/imports")
def import_source(source_id:str, request:Request, body:dict=Body(...), idempotency_key:str|None=Header(None,alias="Idempotency-Key"), db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"importSource"); validate("ImportRequest",body)
    def action():
        src=get_row(db,ctx,"Source",source_id)
        # Transport contract does not define binary upload yet; no path traversal or magical file access is accepted.
        operation=make_operation(db,ctx,"import_source",None,correlation(request),status="failed",error_code="capability_unavailable")
        report=create_entity(db,ctx,"ImportReport",{"source_id":source_id,"operation_id":operation["id"],"status":"failed","read_count":0,"normalized_count":0,"rejected_count":0,"issues":[{"record_ref":body["uploaded_file_ref"],"code":"upload_transport_not_configured","severity":"error","detail":"Le transport binaire doit être fourni par une intégration autorisée."}],"artifact_ref":None},parent_id=source_id,status="failed")
        op_row=get_row(db,ctx,"Operation",operation["id"],for_update=True); update_row(op_row,result_ref=report["id"])
        return op_row.data,202,str(op_row.revision)
    p,s,e=idempotent(db,ctx,"importSource",idempotency_key,body,action); return response(p,s,e)


@router.get("/imports/{operation_id}/report")
def get_import_report(operation_id:str, db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"getImportReport"); operation=get_row(db,ctx,"Operation",operation_id); rid=operation.data.get("result_ref")
    if not rid: raise DomainError("not_found",404,"Rapport d'import absent.")
    item=get_entity(db,ctx,"ImportReport",rid); return response(item,etag=str(item["revision"]))


@router.get("/knowledge/concepts")
def search_concepts(q:str|None=Query(None), db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"searchConcepts")
    items=[syn.concept("SYN-D1"),syn.concept("SYN-T1"),syn.concept("SYN-DRUG"),syn.concept("SYN-Q1"),syn.concept("SYN-OBS1")]
    if q: items=[x for x in items if q.lower() in x["code"].lower() or q.lower() in x["system"].lower()]
    return page(items)


@router.get("/knowledge/assertions")
def search_assertions(subject_code:str|None=Query(None), predicate:str|None=Query(None), object_code:str|None=Query(None), release_id:str|None=Query(None), db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"searchAssertions"); return page([])


@router.get("/knowledge/models")
def list_models(release_id:str|None=Query(None), population_id:str|None=Query(None), db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"listModels"); items=syn.models();
    if population_id: items=[x for x in items if x["scope"]["population_id"]==population_id]
    return page(items)


@router.get("/knowledge/protocols")
def list_protocols(release_id:str|None=Query(None), db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"listProtocols"); return page(syn.protocols())


@router.get("/knowledge/evidence")
def list_evidence(subject_code:str|None=Query(None), release_id:str|None=Query(None), db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"listEvidence"); return page(syn.evidence())


@router.get("/knowledge/optimization-policies")
def list_optimization_policies(db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"listOptimizationPolicies"); return page(syn.optimization_policies())


@router.post("/knowledge/releases")
def build_release(request:Request, body:dict=Body(...), idempotency_key:str|None=Header(None,alias="Idempotency-Key"), db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"buildRelease"); validate("ReleaseBuildRequest",body)
    def action():
        rid=digest(body)
        release={"format":"medikristal.knowledge-release/1","release_id":rid,"version":"0.1.0","status":"candidate","usage":body["intended_use"],"synthetic":body["synthetic"],"files":[],"source_refs":body["source_snapshot_refs"],"model_refs":body["model_refs"],"protocol_refs":body["protocol_refs"],"rights_manifest_ref":artifact_ref("synthetic-rights"),"qualification_refs":[],"minimum_runtime":"0.1.0","built_at":now_iso(),"signatures":[]}
        entity=create_entity(db,ctx,"KnowledgeRelease",release,entity_id=uuid4(),envelope=False,status="candidate",foreign_key=rid)
        row=db.execute(select(Entity).where(Entity.tenant_id==ctx.tenant_id,Entity.kind=="KnowledgeRelease",Entity.foreign_key==rid)).scalar_one()
        operation=make_operation(db,ctx,"build_release",row.id,correlation(request)); return operation,202,str(operation["revision"])
    p,s,e=idempotent(db,ctx,"buildRelease",idempotency_key,body,action); return response(p,s,e)


@router.get("/knowledge/releases/{release_id}")
def get_release(release_id:str, db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"getRelease")
    row=db.execute(select(Entity).where(Entity.tenant_id==ctx.tenant_id,Entity.kind=="KnowledgeRelease",(Entity.id==release_id)|(Entity.foreign_key==release_id))).scalar_one_or_none()
    if not row: raise DomainError("not_found",404,"Release introuvable.")
    return row.data


@router.post("/knowledge/releases/{release_id}/decisions")
def decide_release(release_id:str, request:Request, body:dict=Body(...), idempotency_key:str|None=Header(None,alias="Idempotency-Key"), db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"decideRelease"); validate("ReleaseDecision",body)
    def action():
        row=db.execute(select(Entity).where(Entity.tenant_id==ctx.tenant_id,Entity.kind=="KnowledgeRelease",(Entity.id==release_id)|(Entity.foreign_key==release_id)).with_for_update()).scalar_one_or_none()
        if not row: raise DomainError("not_found",404,"Release introuvable.")
        data=dict(row.data)
        if body["verdict"]=="publish": data["status"]="published"
        else: data["status"]="revoked"
        row.data=data; row.status=data["status"]; row.revision+=1; row.updated_at=utcnow()
        event="knowledge.published" if data["status"]=="published" else "knowledge.revoked"
        emit_event(db,ctx,event,"KnowledgeRelease",row.id,row.revision,correlation(request),{"release_id":data["release_id"],"reason":body["reason"]})
        operation=make_operation(db,ctx,"decide_release",row.id,correlation(request)); return operation,202,str(operation["revision"])
    p,s,e=idempotent(db,ctx,"decideRelease",idempotency_key,body,action); return response(p,s,e)


@router.post("/knowledge/activations")
def activate_release(request:Request, body:dict=Body(...), idempotency_key:str|None=Header(None,alias="Idempotency-Key"), db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"activateRelease"); validate("ReleaseActivation",body)
    def action():
        ref=body["release_ref"]
        row=db.execute(select(Entity).where(Entity.tenant_id==ctx.tenant_id,Entity.kind=="KnowledgeRelease",Entity.foreign_key==ref["digest"])).scalar_one_or_none()
        if row is None: raise DomainError("not_found",404,"Release introuvable.")
        if row.data["status"]!="published": raise DomainError("release_not_admitted",409,"Seule une release publiée peut être activée.")
        if row.data.get("synthetic") and row.data.get("usage")!="engineering": raise DomainError("clinical_use_not_admitted",403,"Une release synthétique ne peut être admise cliniquement.")
        cfg,rev=get_configuration(db,ctx,settings.configuration_default)
        cfg["local_release_ref"]=ref
        state=db.get(ConfigurationState,ctx.tenant_id); state.data=cfg; state.revision+=1; state.updated_at=utcnow()
        operation=make_operation(db,ctx,"activate_release",row.id,correlation(request)); return operation,202,str(operation["revision"])
    p,s,e=idempotent(db,ctx,"activateRelease",idempotency_key,body,action); return response(p,s,e)


@router.post("/knowledge/exports")
def export_knowledge(request:Request, body:dict=Body(...), idempotency_key:str|None=Header(None,alias="Idempotency-Key"), db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"exportKnowledge"); validate("ExportRequest",body)
    def action():
        # Only knowledge metadata is exported; entities with patient/case identifiers are never included.
        result_ref=f"export:{digest(body)[7:23]}"
        operation=make_operation(db,ctx,"export_knowledge",result_ref,correlation(request))
        audit(db,ctx,"knowledge.exported",correlation(request),detail={"target":body["target"],"release":body["release_ref"]})
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
def list_contributions(db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"listContributions"); return page(list_entities(db,ctx,"Contribution"))


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
def set_provider_policy(body:dict=Body(...), idempotency_key:str|None=Header(None,alias="Idempotency-Key"), db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"setProviderPolicy"); validate("ProviderPolicyInput",body)
    cfg,_=get_configuration(db,ctx,settings.configuration_default)
    if body["enabled"] and cfg["mode"]!="online_extended": raise DomainError("unsupported_profile",422,"Un fournisseur payant ne peut être activé hors online_extended.")
    def action():
        item=create_entity(db,ctx,"ProviderPolicy",body,foreign_key=body["provider_id"]); return item,201,str(item["revision"])
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
        get_row(db,ctx,"Evaluation",body["evaluation_id"])
        allergies=[o for o in list_entities(db,ctx,"Observation",parent_id=case_id) if o["kind"]=="allergy" and o["status"]!="entered_in_error"]
        allergy_known=any(o["presence"] in {"present","absent"} for o in allergies)
        option=create_entity(db,ctx,"TreatmentOption",syn.treatment_option(case.data,allergy_known),parent_id=case_id,status="proposed" if allergy_known else "needs_information")
        operation=make_operation(db,ctx,"evaluate_treatments",option["id"],correlation(request)); return operation,202,str(operation["revision"])
    p,s,e=idempotent(db,ctx,"evaluateTreatments",idempotency_key,body,action); return response(p,s,e)


@router.get("/cases/{case_id}/treatment-options")
def list_treatment_options(case_id:str, db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"listTreatmentOptions"); get_row(db,ctx,"ClinicalCase",case_id); return page(list_entities(db,ctx,"TreatmentOption",parent_id=case_id))


@router.get("/configuration")
def get_configuration_api(db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"getConfiguration"); cfg,rev=get_configuration(db,ctx,settings.configuration_default); return response(cfg,etag=str(rev))


@router.post("/configuration/changes")
def change_configuration(request:Request, body:dict=Body(...), idempotency_key:str|None=Header(None,alias="Idempotency-Key"), if_match:str|None=Header(None,alias="If-Match"), db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"changeConfiguration"); validate("Configuration",body)
    def action():
        current,rev=get_configuration(db,ctx,settings.configuration_default)
        expected=int(if_match.strip('W/"')) if if_match else None
        if expected is None: raise DomainError("precondition_required",428,"If-Match est requis.")
        if expected!=rev: raise DomainError("precondition_failed",412,"La configuration a changé.")
        if body["mode"]=="offline_free" and body["network_scope"]=="internet": raise DomainError("unsupported_profile",422,"offline_free interdit le WAN.")
        if body["mode"] in {"offline_free","online_free"} and body["paid_budget_minor"]!=0: raise DomainError("unsupported_profile",422,"Ce mode interdit un budget payant.")
        if body["intended_use"]=="clinical_execution" and body["execution_policy"]!="protocol_authorized": raise DomainError("clinical_use_not_admitted",422,"clinical_execution exige une politique d'exécution admise.")
        state=db.get(ConfigurationState,ctx.tenant_id); state.data=body; state.revision+=1; state.updated_at=utcnow()
        audit(db,ctx,"configuration.changed",correlation(request),detail={"from":current["mode"],"to":body["mode"]})
        return body,200,str(state.revision)
    p,s,e=idempotent(db,ctx,"changeConfiguration",idempotency_key,body,action); return response(p,s,e)


# Versioned catalogs: sites, managed resources, procedure catalog.
def _register_catalog_routes() -> None:
    specs=[
        ("/sites","Site","SiteInput","SiteRevision","listSite","createSite","getSite","reviseSite"),
        ("/managed-resources","ManagedResource","ManagedResourceInput","ManagedResourceRevision","listManagedResource","createManagedResource","getManagedResource","reviseManagedResource"),
        ("/procedure-catalog","ProcedureEntry","ProcedureEntryInput","ProcedureEntryRevision","listProcedureEntry","createProcedureEntry","getProcedureEntry","reviseProcedureEntry"),
    ]
    for path,kind,input_schema,revision_schema,list_op,create_op,get_op,revise_op in specs:
        def list_handler(db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context), _kind=kind, _op=list_op, site_id:str|None=Query(None), q:str|None=Query(None), family:str|None=Query(None)):
            op(ctx,_op); items=list_entities(db,ctx,_kind)
            if _kind=="ManagedResource" and site_id: items=[x for x in items if x.get("site_id")==site_id]
            if _kind=="ProcedureEntry" and family: items=[x for x in items if x.get("family")==family]
            if _kind=="ProcedureEntry" and q: items=[x for x in items if q.lower() in x.get("concept",{}).get("code","").lower()]
            return page(items)
        def create_handler(body:dict=Body(...), idempotency_key:str|None=Header(None,alias="Idempotency-Key"), db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context), _kind=kind,_schema=input_schema,_op=create_op):
            op(ctx,_op)
            def action():
                item=catalog_create(_kind,_schema,body,db,ctx)
                if _kind=="ManagedResource": get_row(db,ctx,"Site",body["site_id"])
                return item,201,str(item["revision"])
            p,s,e=idempotent(db,ctx,_op,idempotency_key,body,action); return response(p,s,e)
        def get_handler(item_id:str, db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context), _kind=kind,_op=get_op):
            op(ctx,_op); item=get_entity(db,ctx,_kind,item_id); return response(item,etag=str(item["revision"]))
        def revise_handler(item_id:str, request:Request, body:dict=Body(...), idempotency_key:str|None=Header(None,alias="Idempotency-Key"), if_match:str|None=Header(None,alias="If-Match"), db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context), _kind=kind,_schema=revision_schema,_op=revise_op):
            op(ctx,_op)
            def action():
                item=catalog_revise(_kind,_schema,item_id,body,if_match,db,ctx)
                emit_event(db,ctx,"catalog.changed",_kind,item_id,item["revision"],correlation(request),{"reason":body["reason"]})
                return item,200,str(item["revision"])
            p,s,e=idempotent(db,ctx,_op,idempotency_key,body,action); return response(p,s,e)
        router.add_api_route(path,list_handler,methods=["GET"],name=list_op)
        router.add_api_route(path,create_handler,methods=["POST"],name=create_op)
        router.add_api_route(path+"/{item_id}",get_handler,methods=["GET"],name=get_op)
        router.add_api_route(path+"/{item_id}/revisions",revise_handler,methods=["POST"],name=revise_op)

_register_catalog_routes()


@router.post("/workflows")
def create_workflow(body:dict=Body(...), idempotency_key:str|None=Header(None,alias="Idempotency-Key"), db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"createWorkflow"); validate("WorkflowInput",body)
    def action():
        case=get_row(db,ctx,"ClinicalCase",body["case_id"]); require_case_revision(case,body["case_revision"])
        status="ready" if body["protocol_ref"]["id"]==syn.PROTOCOL["id"] else "paused"
        reasons=[] if status=="ready" else ["capability_unavailable"]
        item=create_entity(db,ctx,"WorkflowRun",{**body,"status":status,"current_step_ids":["evaluate"] if status=="ready" else [],"reason_codes":reasons},parent_id=case.id,status=status)
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
def list_case_workflows(case_id:str, db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"listCaseWorkflows"); get_row(db,ctx,"ClinicalCase",case_id); return page(list_entities(db,ctx,"WorkflowRun",parent_id=case_id))


@router.post("/cases/{case_id}/result-batches")
def receive_result_batch(case_id:str, request:Request, body:dict=Body(...), idempotency_key:str|None=Header(None,alias="Idempotency-Key"), if_match:str|None=Header(None,alias="If-Match"), db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"receiveResultBatch"); validate("ResultBatchInput",body)
    def action():
        case=get_row(db,ctx,"ClinicalCase",case_id,for_update=True); enforce_match(case,if_match); require_case_revision(case,body["case_revision"])
        canonical={k:body[k] for k in ("owner","report_id","report_version","items")}
        calculated=digest(canonical)
        if body["digest"]!=calculated: raise DomainError("artifact_integrity_failed",422,"Le digest du rapport ne correspond pas à sa représentation canonique.")
        ext=db.execute(select(ExternalVersion).where(ExternalVersion.tenant_id==ctx.tenant_id,ExternalVersion.namespace==f"result-report:{body['owner']}",ExternalVersion.foreign_id==body["report_id"],ExternalVersion.foreign_version==body["report_version"])).scalar_one_or_none()
        if ext:
            if ext.digest!=body["digest"]: raise DomainError("source_version_conflict",409,"Même version de rapport avec contenu divergent.")
            receipt=get_entity(db,ctx,"ResultReceipt",ext.entity_id); return receipt,200,str(receipt["revision"])
        observations=[]
        # Validate all links first, then persist atomically.
        for item in body["items"]:
            if item.get("replaces_id"): get_row(db,ctx,"Observation",item["replaces_id"])
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
            create_entity(db,ctx,"FollowUpTask",{"case_id":case_id,"origin_ref":f"result-receipt:{receipt['id']}","owner_ref":None,"due_at":now_iso(),"reason":"Résultat reçu après clôture; propriétaire à attribuer.","status":"open","completion_ref":None},parent_id=case_id,status="open")
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
def list_case_followups(case_id:str, db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"listCaseFollowUps"); get_row(db,ctx,"ClinicalCase",case_id); return page(list_entities(db,ctx,"FollowUpTask",parent_id=case_id))


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
def list_case_care_plans(case_id:str, db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"listCaseCarePlans"); get_row(db,ctx,"ClinicalCase",case_id); return page(list_entities(db,ctx,"CarePlan",parent_id=case_id))


@router.get("/care-plans/{plan_id}")
def get_care_plan(plan_id:str, db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"getCarePlan"); item=get_entity(db,ctx,"CarePlan",plan_id); return response(item,etag=str(item["revision"]))


@router.post("/care-plans/{plan_id}/revisions")
def revise_care_plan(plan_id:str, request:Request, body:dict=Body(...), idempotency_key:str|None=Header(None,alias="Idempotency-Key"), if_match:str|None=Header(None,alias="If-Match"), db:Session=Depends(get_session), ctx:AuthContext=Depends(auth_context)):
    op(ctx,"reviseCarePlan"); validate("CarePlanRevision",body)
    def action():
        row=get_row(db,ctx,"CarePlan",plan_id,for_update=True); enforce_match(row,if_match)
        case=get_row(db,ctx,"ClinicalCase",row.parent_id); require_case_revision(case,body["replacement"]["case_revision"])
        item=update_row(row,replacement={**body["replacement"],"case_id":case.id,"status":body["status"]})
        emit_event(db,ctx,"care_plan.changed","CarePlan",plan_id,item["revision"],correlation(request),{"status":body["status"],"reason":body["reason"]})
        return item,200,str(item["revision"])
    p,s,e=idempotent(db,ctx,"reviseCarePlan",idempotency_key,body,action); return response(p,s,e)
