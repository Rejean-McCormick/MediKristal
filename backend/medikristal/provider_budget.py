from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import Entity
from .errors import DomainError
from .security import AuthContext
from .store import get_configuration, update_row


def reserve_provider_budget(session: Session, ctx: AuthContext, provider_id: str, amount_minor: int, default_config: dict) -> dict:
    """Atomically reserve provider budget on its policy row.

    Kept as an internal service because the v0.2 transport contract has no provider invocation endpoint.
    A reservation is retained if the remote outcome is unknown; reconciliation must release or spend it.
    """
    if amount_minor < 0:
        raise DomainError("invalid_request", 422, "Montant de réserve invalide.")
    config, _ = get_configuration(session, ctx, default_config)
    if config["mode"] != "online_extended":
        raise DomainError("unsupported_profile", 422, "Les fournisseurs payants exigent online_extended.")
    row = session.execute(select(Entity).where(
        Entity.tenant_id == ctx.tenant_id,
        Entity.kind == "ProviderPolicy",
        Entity.foreign_key == provider_id,
    ).order_by(Entity.created_at.desc()).with_for_update()).scalars().first()
    if row is None or not row.data.get("enabled"):
        raise DomainError("capability_unavailable", 503, "Fournisseur non activé.", retryable=False)
    data = dict(row.data)
    reserved = int(data.get("_reserved_minor", 0))
    spent = int(data.get("_spent_minor", 0))
    if spent + reserved + amount_minor > int(data["budget_minor"]):
        raise DomainError("budget_exceeded", 409, "Budget fournisseur insuffisant.")
    data["_reserved_minor"] = reserved + amount_minor
    return update_row(row, **data)


def reconcile_provider_budget(session: Session, ctx: AuthContext, provider_id: str, amount_minor: int, outcome: str) -> dict:
    row = session.execute(select(Entity).where(
        Entity.tenant_id == ctx.tenant_id,
        Entity.kind == "ProviderPolicy",
        Entity.foreign_key == provider_id,
    ).order_by(Entity.created_at.desc()).with_for_update()).scalars().first()
    if row is None:
        raise DomainError("not_found", 404, "Politique fournisseur introuvable.")
    data = dict(row.data)
    reserved = int(data.get("_reserved_minor", 0))
    if amount_minor > reserved:
        raise DomainError("provider_outcome_unknown", 409, "Réserve fournisseur incohérente; réconciliation requise.")
    if outcome == "spent":
        data["_reserved_minor"] = reserved - amount_minor
        data["_spent_minor"] = int(data.get("_spent_minor", 0)) + amount_minor
    elif outcome == "released":
        data["_reserved_minor"] = reserved - amount_minor
    elif outcome == "unknown":
        return row.data
    else:
        raise DomainError("invalid_request", 422, "Issue de réconciliation inconnue.")
    return update_row(row, **data)
