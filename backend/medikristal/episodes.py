"""Episode workflow, with explicit capabilities for every mutation."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Annotated, Literal
from uuid import UUID, uuid5, NAMESPACE_URL

from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.openapi.utils import get_openapi
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .config import load_settings
from .db import Entity, EpisodeAnalysis, ExternalVersion, ReservationClaim, get_session, utcnow
from .episode_catalog import public_lookup
from .episode_rules import DEMO_PACKAGE, DEMO_PACKAGE_REF, DEFAULT_RESOURCES, OBSERVATIONS, RESULTS, TESTS, assessment, plans
from .errors import DomainError
from .security import AuthContext, auth_context
from .store import audit, create_entity, emit_event, enforce_match, expected_revision, get_row, grant_case_access, idempotent, list_entities, register_external_version, update_row
from .util import digest, now_iso, uuid4

routes = APIRouter(prefix="/api/v2")
settings = load_settings()
LOOPBACK = {"127.0.0.1", "localhost", "::1"}
LOCAL = AuthContext("00000000-0000-4000-8000-000000000001", "atelier-local", frozenset({"episode:*"}))
TestCode = Literal["screen", "direct", "confirm"]
ObservationCode = Literal["discomfort", "itch", "alarm"]
ResultCode = Literal["positive", "negative", "indeterminate", "unusable", "not_performed"]
WriteKey = Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=200)]
Match = Annotated[str, Header(alias="If-Match", max_length=64)]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Start(Input):
    title: Annotated[str, StringConstraints(min_length=1, max_length=120)]


class Observations(Input):
    values: dict[ObservationCode, Literal["present", "absent", "unknown", "not_assessed"]] = Field(min_length=1)


class Order(Input):
    test: TestCode


class LabResult(Input):
    value: ResultCode
    version: int = Field(ge=1, le=10000)


class Decision(Input):
    disposition: Literal["accept", "escalate"]
    note: Annotated[str, StringConstraints(max_length=500)] = ""


class VerifiedOutcome(Input):
    value: Literal["confirmed", "excluded", "unverified"]
    evidence: Annotated[str, StringConstraints(min_length=1, max_length=300)]


class CancelOrder(Input):
    reason: Annotated[str, StringConstraints(min_length=1, max_length=300)]


class Consent(Input):
    include: bool


class Grant(Input):
    principal: Annotated[str, StringConstraints(min_length=1, max_length=128)]


class Capacity(Input):
    minutes: int | None = Field(ge=1, le=1440)
    cost_minor: int | None = Field(ge=0, le=100000000)
    capacity: int = Field(ge=0, le=100)


def access(request: Request, authorization: Annotated[str | None, Header()] = None) -> AuthContext:
    if authorization is not None or not settings.local_episode_demo:
        return auth_context(request, authorization)
    origin = request.headers.get("origin")
    allowed_origins = {f"http://{request.url.netloc}", f"https://{request.url.netloc}"}
    if request.url.hostname not in LOOPBACK or (origin and origin not in allowed_origins):
        raise DomainError("authentication_required", 401, "L’atelier est accessible depuis son adresse locale.")
    return LOCAL


Context = Annotated[AuthContext, Depends(access)]
Database = Annotated[Session, Depends(get_session)]


def require(ctx: AuthContext, permission: str) -> None:
    if not ctx.permits(f"episode:{permission}"):
        raise DomainError("permission_denied", 403, "Votre rôle ne permet pas cette action.")


def conflict(detail: str) -> DomainError:
    return DomainError("episode_conflict", 409, detail)


def resource_id(ctx: AuthContext, code: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"urn:medikristal:{ctx.tenant_id}:demo-capacity:{code}"))


def rows_for_resources(db: Session, ctx: AuthContext, *, lock: bool = False) -> dict:
    keys = {resource_id(ctx, code): code for code in TESTS}
    query = select(Entity).where(Entity.id.in_(keys), Entity.tenant_id == ctx.tenant_id,
                                 Entity.kind == "EpisodeCapacity").order_by(Entity.id)
    if lock:
        query = query.with_for_update()
    return {keys[row.id]: row for row in db.scalars(query)}


def seed_resources(db: Session, ctx: AuthContext) -> None:
    existing = rows_for_resources(db, ctx)
    for code in sorted(TESTS, key=lambda item: resource_id(ctx, item)):
        if code in existing:
            continue
        try:
            with db.begin_nested():
                create_entity(db, ctx, "EpisodeCapacity", DEFAULT_RESOURCES[code],
                              entity_id=resource_id(ctx, code))
        except IntegrityError:
            get_row(db, ctx, "EpisodeCapacity", resource_id(ctx, code))


def resource_view(db: Session, ctx: AuthContext, *, lock: bool = False) -> dict:
    rows = rows_for_resources(db, ctx, lock=lock)
    usage = dict(db.execute(select(ReservationClaim.capability_id, func.count())
        .where(ReservationClaim.tenant_id == ctx.tenant_id,
               ReservationClaim.slot_id == "episode-simulator")
        .group_by(ReservationClaim.capability_id)).all())
    view = {}
    for code, defaults in DEFAULT_RESOURCES.items():
        row = rows.get(code)
        data = row.data if row else defaults
        view[code] = {field: data[field] for field in defaults}
        view[code].update(available=max(0, data["capacity"] - usage.get(resource_id(ctx, code), 0)),
                          revision=row.revision if row else 1, label=TESTS[code])
    return view


def release_claim(db: Session, ctx: AuthContext, order_id: str) -> None:
    db.execute(delete(ReservationClaim).where(ReservationClaim.tenant_id == ctx.tenant_id,
                                             ReservationClaim.booking_id == order_id))


def state_of(db: Session, ctx: AuthContext, episode: dict, *, lock_resources: bool = False) -> dict:
    resources = resource_view(db, ctx, lock=lock_resources)
    assessment_now = episode["assessment"]
    remaining = max(0.0, (datetime.fromisoformat(episode["deadline"]) - utcnow()).total_seconds() / 60)
    options = [] if episode["order"] else plans(
        assessment_now, episode["results"], resources, remaining, episode["package"],
    )
    return {
        **{key: value for key, value in episode.items() if key not in {"package", "decision", "access_owner", "outcome", "prediction"}},
        "decision": episode["decision"], "choices": options,
        "outcome_verified": (episode.get("outcome") or {}).get("value") in {"confirmed", "excluded"},
        "procedure": episode["package"]["procedure"], "model": episode["package"]["model"],
    }


def project_analysis(db: Session, ctx: AuthContext, episode: dict) -> None:
    current = db.get(EpisodeAnalysis, episode["id"])
    if not episode["sharing"] or episode["status"] != "closed":
        if current is not None:
            db.delete(current)
        return
    if current is None:
        current = EpisodeAnalysis(episode_id=episode["id"], tenant_id=ctx.tenant_id)
        db.add(current)
    prediction = episode.get("prediction") or {}
    outcome = (episode.get("outcome") or {}).get("value")
    current.outcome_kind = (episode["decision"]["kind"] if episode["decision"]["disposition"] == "accept"
                            else "transferred")
    current.model_ref = episode["package_ref"]
    current.forecast_percent = prediction.get("value_percent")
    current.verified_positive = {"confirmed": True, "excluded": False}.get(outcome)


def changed(db: Session, ctx: AuthContext, request: Request, row: Entity, event: str, **updates) -> dict:
    data = update_row(row, **updates)
    if event in {"episode.result.received", "episode.decision.recorded", "episode.outcome.verified",
                 "episode.statistics.consent"}:
        project_analysis(db, ctx, data)
    corr = request.state.correlation_id
    emit_event(db, ctx, event, "Episode", row.id, row.revision, corr, {"episode_id": row.id})
    audit(db, ctx, event, corr, target_kind="Episode", target_id=row.id)
    return data


def command(db: Session, ctx: AuthContext, key: str, name: str, body: dict, run):
    payload, status, etag = idempotent(db, ctx, f"episode.{name}", key, body, run)
    # Commit before returning a successful response.
    db.commit()
    return ORJSONResponse(payload, status_code=status, headers={"ETag": f'"{etag}"'} if etag else {})


@routes.get("/openapi.json", include_in_schema=False)
def episode_schema():
    return get_openapi(title="MediKristal — Épisodes", version="2.0.0", routes=routes.routes)


@routes.get("/catalog")
def catalog(ctx: Context):
    require(ctx, "read")
    return {"observations": OBSERVATIONS, "results": RESULTS, "mode": "simulation",
            "permissions": {name: ctx.permits(f"episode:{name}") and (ctx is not LOCAL or name not in {"verify", "share"}) for name in
                            ("collect", "order", "lab", "sign", "resources", "statistics", "share", "verify")}}


@routes.get("/episodes")
def episodes(ctx: Context, db: Database):
    require(ctx, "read")
    return [{key: episode[key] for key in ("id", "title", "revision", "updated_at", "status")}
            for episode in reversed(list_entities(db, ctx, "Episode"))]


@routes.post("/episodes", status_code=201)
def start(body: Start, ctx: Context, db: Database, key: WriteKey, request: Request):
    require(ctx, "collect")

    def run():
        seed_resources(db, ctx)
        data = create_entity(db, ctx, "Episode", {
            "title": body.title, "status": "open", "observations": {}, "results": {},
            "order": None, "decision": None, "decision_needs_review": False, "sharing": False,
            "assessment": assessment({}, {}), "package": DEMO_PACKAGE, "package_ref": DEMO_PACKAGE_REF,
            "access_owner": ctx.principal_id,
            "deadline": (utcnow() + timedelta(minutes=DEMO_PACKAGE["procedure"]["deadline_minutes"])).isoformat(),
        })
        emit_event(db, ctx, "episode.opened", "Episode", data["id"], data["revision"],
                   request.state.correlation_id, {"episode_id": data["id"]})
        return state_of(db, ctx, data), 201, str(data["revision"])

    return command(db, ctx, key, "start", body.model_dump(), run)


@routes.get("/episodes/{episode_id}")
def episode(episode_id: UUID, ctx: Context, db: Database):
    require(ctx, "read")
    row = get_row(db, ctx, "Episode", str(episode_id))
    return ORJSONResponse(state_of(db, ctx, row.data), headers={"ETag": f'"{row.revision}"'})


@routes.get("/episodes/{episode_id}/projection")
def episode_projection(episode_id: UUID, ctx: Context, db: Database):
    require(ctx, "read")
    require(ctx, "export")
    row = get_row(db, ctx, "Episode", str(episode_id))
    data = row.data
    projection = {
        "format": "medikristal.episode-projection/1",
        "classification": "restricted",
        "recipe_candidate": "dossier-medical",
        "profile": "simulation",
        "reference": {"id": row.id, "revision": row.revision, "package": data["package_ref"]},
        "procedure": data["package"]["procedure"],
        "observations": data["observations"],
        "result_states": data["results"],
        "assessment": data["assessment"],
        "disposition": data["decision"]["disposition"] if data["decision"] else None,
        "review_required": data["decision_needs_review"],
    }
    return {**projection, "digest": digest(projection)}


def episode_command(episode_id: UUID, ctx: Context, db: Database, key: str, match: str,
                    permission: str, name: str, body: Input, apply):
    require(ctx, permission)

    def run():
        row = get_row(db, ctx, "Episode", str(episode_id), for_update=True)
        enforce_match(row, match)
        data = apply(row)
        return state_of(db, ctx, data), 200, str(data["revision"])

    return command(db, ctx, key, name, {"episode": str(episode_id), "body": body.model_dump()}, run)


@routes.post("/episodes/{episode_id}/observations")
def collect(episode_id: UUID, body: Observations, request: Request, ctx: Context,
            db: Database, key: WriteKey, match: Match):
    def apply(row):
        data = row.data
        if data["status"] != "open":
            raise conflict("Cet épisode est clôturé.")
        values = {**data["observations"], **body.values}
        authors = {**data.get("observation_sources", {}), **{
            code: {"principal": ctx.principal_id, "recorded_at": now_iso(),
                   "origin": "observed" if ctx.permits("episode:sign") else "reported"}
            for code in body.values
        }}
        return changed(db, ctx, request, row, "episode.observed", observations=values,
                       observation_sources=authors, assessment=assessment(values, data["results"], data["package"]))

    return episode_command(episode_id, ctx, db, key, match, "collect", "collect", body, apply)


@routes.post("/episodes/{episode_id}/grants")
def grant(episode_id: UUID, body: Grant, request: Request, ctx: Context,
          db: Database, key: WriteKey, match: Match):
    def apply(row):
        if ctx.principal_id != row.data["access_owner"]:
            raise DomainError("permission_denied", 403, "Seul le créateur peut transmettre cet épisode.")
        grant_case_access(db, ctx, row.id, body.principal)
        return changed(db, ctx, request, row, "episode.shared")

    return episode_command(episode_id, ctx, db, key, match, "share", "grant", body, apply)


@routes.post("/episodes/{episode_id}/orders")
def order(episode_id: UUID, body: Order, request: Request, ctx: Context,
          db: Database, key: WriteKey, match: Match):
    def apply(row):
        if row.data["status"] != "open" or row.data["order"]:
            raise conflict("Une demande est déjà engagée ou l’épisode est clôturé.")
        current = state_of(db, ctx, row.data, lock_resources=True)
        selected = next((item for item in current["choices"] if item["test"] == body.test), None)
        if not selected or not selected["available"]:
            raise conflict("Le parcours a changé. Actualisez la fiche pour voir les options disponibles.")
        cid = resource_id(ctx, body.test)
        occupied = set(db.scalars(select(ReservationClaim.unit_index).where(
            ReservationClaim.tenant_id == ctx.tenant_id, ReservationClaim.capability_id == cid,
            ReservationClaim.slot_id == "episode-simulator",
        )))
        index = next(i for i in range(100) if i not in occupied)
        lab = create_entity(db, ctx, "EpisodeLab", {
            "test": body.test, "issued_by": ctx.principal_id, "status": "waiting",
            "result": None, "result_version": 0, "quote": selected,
        }, parent_id=row.id)
        db.add(ReservationClaim(id=uuid4(), tenant_id=ctx.tenant_id, capability_id=cid,
                                slot_id="episode-simulator", unit_index=index, booking_id=lab["id"],
                                created_at=utcnow()))
        prediction = row.data.get("prediction")
        estimate = row.data["assessment"].get("estimate")
        if prediction is None and estimate is not None:
            prediction = {**estimate, "episode_revision": row.revision, "recorded_at": now_iso(),
                          "model_ref": row.data["package_ref"], "observer": ctx.principal_id}
        return changed(db, ctx, request, row, "episode.order.accepted_by_simulator",
                       prediction=prediction, order={"id": lab["id"], "test": body.test, "label": TESTS[body.test], "status": "waiting"})

    return episode_command(episode_id, ctx, db, key, match, "order", "order", body, apply)


@routes.post("/episodes/{episode_id}/orders/{order_id}/result")
def lab_result(episode_id: UUID, order_id: UUID, body: LabResult, request: Request,
               ctx: Context, db: Database, key: WriteKey, match: Match):
    require(ctx, "lab")

    def run():
        row = get_row(db, ctx, "Episode", str(episode_id), for_update=True)
        lab = get_row(db, ctx, "EpisodeLab", str(order_id), for_update=True)
        if lab.parent_id != row.id:
            raise DomainError("not_found", 404, "Demande introuvable dans cet épisode.")
        expected_revision(match)
        namespace = f"episode-result:{lab.id}"
        canonical = body.model_dump()
        existing = db.scalar(select(ExternalVersion).where(ExternalVersion.tenant_id == ctx.tenant_id,
                              ExternalVersion.namespace == namespace, ExternalVersion.foreign_id == lab.id,
                              ExternalVersion.foreign_version == str(body.version)))
        if existing:
            if existing.digest != digest(canonical):
                raise conflict("Cette version a déjà été reçue avec un autre contenu.")
            return state_of(db, ctx, row.data), 200, str(row.revision)
        if lab.data["status"] == "cancelled":
            raise conflict("Cette demande a été annulée par le laboratoire simulé.")
        enforce_match(row, match)
        if body.version != lab.data["result_version"] + 1:
            raise conflict("La version précédente du résultat doit être reçue d’abord.")
        if row.data["order"] and row.data["order"]["id"] != lab.id:
            # Retain the active order, with its claim. Corrections still update findings.
            active_order = row.data["order"]
        else:
            active_order = None
        update_row(lab, status="reported", result=body.value,
                   result_version=body.version, reported_by=ctx.principal_id)
        release_claim(db, ctx, lab.id)
        register_external_version(db, ctx, namespace, lab.id, str(body.version), canonical, lab.id)
        results = {**row.data["results"], lab.data["test"]: body.value}
        history = {**row.data.get("reported_orders", {}), lab.id: {
            "id": lab.id, "label": TESTS[lab.data["test"]], "value": body.value,
            "result_version": body.version, "reported_at": now_iso(),
        }}
        data = changed(db, ctx, request, row, "episode.result.received", order=active_order,
                       results=results, reported_orders=history, status="open",
                       decision_needs_review=bool(row.data["decision"]),
                       assessment=assessment(row.data["observations"], results, row.data["package"]),
                       outcome=None)
        return state_of(db, ctx, data), 200, str(row.revision)

    return command(db, ctx, key, "result", {"episode": str(episode_id), "order": str(order_id),
                                          "body": body.model_dump()}, run)


@routes.post("/episodes/{episode_id}/orders/{order_id}/cancel")
def cancel_order(episode_id: UUID, order_id: UUID, body: CancelOrder, request: Request,
                 ctx: Context, db: Database, key: WriteKey, match: Match):
    def apply(row):
        order_state = row.data["order"]
        if not order_state or order_state["id"] != str(order_id):
            raise conflict("La demande n’est plus en attente.")
        lab = get_row(db, ctx, "EpisodeLab", str(order_id), for_update=True)
        update_row(lab, status="cancelled", cancellation_reason=body.reason, cancelled_by=ctx.principal_id)
        release_claim(db, ctx, lab.id)
        return changed(db, ctx, request, row, "episode.order.cancelled_by_simulator", order=None)

    return episode_command(episode_id, ctx, db, key, match, "order", f"cancel.{order_id}", body, apply)


@routes.post("/episodes/{episode_id}/decision")
def decide(episode_id: UUID, body: Decision, request: Request, ctx: Context,
           db: Database, key: WriteKey, match: Match):
    def apply(row):
        data = row.data
        state = data["assessment"]
        if data["status"] != "open" or data["order"]:
            raise conflict("Une demande doit être résolue avant la clôture.")
        if body.disposition == "accept" and state.get("review_kind") not in {"confirmed", "excluded", "no_indication"}:
            raise conflict("Le scénario exige une revue ou une orientation de l’équipe.")
        if body.disposition == "escalate" and not body.note:
            raise DomainError("invalid_request", 422, "Ajoutez le motif du transfert.")
        decision = {"disposition": body.disposition, "reason": state["reason"], "note": body.note,
                    "principal": ctx.principal_id, "signed_at": now_iso(), "signed_revision": row.revision,
                    "summary": "Suivi fictif A" if state.get("review_kind") == "confirmed"
                               and body.disposition == "accept" else "Décision documentée",
                    "kind": state.get("review_kind", "unresolved")}
        return changed(db, ctx, request, row, "episode.decision.recorded", status="closed",
                       decision=decision, decision_needs_review=False)

    return episode_command(episode_id, ctx, db, key, match, "sign", "decide", body, apply)


@routes.post("/episodes/{episode_id}/verified-outcome")
def verify_outcome(episode_id: UUID, body: VerifiedOutcome, request: Request, ctx: Context,
                   db: Database, key: WriteKey, match: Match):
    def apply(row):
        data = row.data
        prediction = data.get("prediction")
        if data["status"] != "closed" or not prediction:
            raise conflict("Une prédiction figée et un épisode clôturé sont requis.")
        if ctx.principal_id in {prediction["observer"], data["decision"]["principal"]}:
            raise DomainError("permission_denied", 403, "L’issue exige un vérificateur distinct.")
        return changed(db, ctx, request, row, "episode.outcome.verified", outcome={
            **body.model_dump(), "verified_by": ctx.principal_id, "recorded_at": now_iso(),
            "revision": row.revision,
        })

    return episode_command(episode_id, ctx, db, key, match, "verify", "verify", body, apply)


@routes.post("/episodes/{episode_id}/statistics-consent")
def consent(episode_id: UUID, body: Consent, request: Request, ctx: Context,
            db: Database, key: WriteKey, match: Match):
    def apply(row):
        if ctx.principal_id != row.data["access_owner"]:
            raise DomainError("permission_denied", 403, "Le choix de contribution relève du créateur.")
        return changed(db, ctx, request, row, "episode.statistics.consent", sharing=body.include)

    return episode_command(episode_id, ctx, db, key, match, "collect", "consent", body, apply)


@routes.get("/resources")
def resources(ctx: Context, db: Database):
    require(ctx, "resources")
    return resource_view(db, ctx)


@routes.put("/resources/{code}")
def edit_resource(code: TestCode, body: Capacity, ctx: Context, db: Database, key: WriteKey, match: Match):
    require(ctx, "resources")

    def run():
        seed_resources(db, ctx)
        row = get_row(db, ctx, "EpisodeCapacity", resource_id(ctx, code), for_update=True)
        enforce_match(row, match)
        update_row(row, **body.model_dump())
        data = resource_view(db, ctx)
        return data, 200, str(row.revision)

    return command(db, ctx, key, f"capacity.{code}", body.model_dump(), run)


@routes.get("/statistics")
def statistics(ctx: Context, db: Database):
    require(ctx, "statistics")
    scope = EpisodeAnalysis.tenant_id == ctx.tenant_id
    counts = dict(db.execute(select(EpisodeAnalysis.outcome_kind, func.count())
                             .where(scope).group_by(EpisodeAnalysis.outcome_kind)).all())
    evaluated = db.execute(select(EpisodeAnalysis.forecast_percent, EpisodeAnalysis.verified_positive)
                           .where(scope, EpisodeAnalysis.model_ref == DEMO_PACKAGE_REF,
                                  EpisodeAnalysis.forecast_percent.is_not(None),
                                  EpisodeAnalysis.verified_positive.is_not(None)))
    errors = [(prediction / 100 - int(actual)) ** 2 for prediction, actual in evaluated]
    return {"scenario_counts": counts, "verified_evaluation": {
                "count": len(errors), "brier": sum(errors) / len(errors) if errors else None,
            }, "model": DEMO_PACKAGE["model"], "model_ref": DEMO_PACKAGE_REF}


@routes.get("/hospital-ops")
def hospital_ops(ctx: Context):
    require(ctx, "read")
    return {"format": "medikristal.hospital-ops-projection/1", "profile": "simulation",
            "procedure": DEMO_PACKAGE["procedure"], "artifact": DEMO_PACKAGE_REF}

@routes.get("/references")
def search_references(ctx: Context, q: Annotated[str, Query(min_length=1, max_length=120)],
                      limit: Annotated[int, Query(ge=1, le=50)] = 15):
    require(ctx, "read")
    return {"items": public_lookup(q.strip(), limit)}
