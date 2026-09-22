from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import ConfigurationState, Entity
from .errors import DomainError
from .security import AuthContext
from .store import get_configuration, update_row


def _parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _policy_row(session: Session, ctx: AuthContext, provider_id: str, *, lock: bool = True) -> Entity:
    stmt = select(Entity).where(
        Entity.tenant_id == ctx.tenant_id,
        Entity.kind == "ProviderPolicy",
        Entity.foreign_key == provider_id,
    ).order_by(Entity.created_at.desc())
    if lock:
        stmt = stmt.with_for_update()
    row = session.execute(stmt).scalars().first()
    if row is None:
        raise DomainError("capability_unavailable", 503, "Fournisseur non activé.", retryable=False)
    return row


def reserve_provider_budget(session: Session, ctx: AuthContext, provider_id: str, amount_minor: int, default_config: dict) -> dict:
    """Reserve both provider and tenant paid budgets transactionally.

    The configuration row is locked before the provider row so reservations for distinct
    providers still serialize against the tenant-wide budget on databases supporting
    row-level locks. An unknown remote outcome deliberately keeps the reservation held.
    """
    if amount_minor < 0:
        raise DomainError("invalid_request", 422, "Montant de réserve invalide.")

    config, _ = get_configuration(session, ctx, default_config)
    cfg_row = session.execute(select(ConfigurationState).where(
        ConfigurationState.tenant_id == ctx.tenant_id
    ).with_for_update()).scalar_one()
    config = dict(cfg_row.data)

    if config["mode"] != "online_extended" or config.get("network_scope") != "internet":
        raise DomainError("unsupported_profile", 422, "Les fournisseurs payants exigent online_extended avec accès internet.")
    if provider_id not in set(config.get("provider_allowlist", [])):
        raise DomainError("capability_unavailable", 503, "Fournisseur absent de l'allowlist active.", retryable=False)

    row = _policy_row(session, ctx, provider_id)
    data = dict(row.data)
    if not data.get("enabled") or config["mode"] not in set(data.get("allowed_modes", [])):
        raise DomainError("capability_unavailable", 503, "Fournisseur non admis dans le mode courant.", retryable=False)
    if data.get("currency") != config.get("currency"):
        raise DomainError("unsupported_profile", 422, "La devise fournisseur ne correspond pas au budget du tenant.")

    now = datetime.now(timezone.utc)
    if not (_parse_ts(data["period_start"]) <= now < _parse_ts(data["period_end"])):
        raise DomainError("budget_exceeded", 409, "La période budgétaire du fournisseur n'est pas active.")

    reserved = int(data.get("_reserved_minor", 0))
    spent = int(data.get("_spent_minor", 0))
    if spent + reserved + amount_minor > int(data["budget_minor"]):
        raise DomainError("budget_exceeded", 409, "Budget fournisseur insuffisant.")

    policies = session.execute(select(Entity).where(
        Entity.tenant_id == ctx.tenant_id,
        Entity.kind == "ProviderPolicy",
    ).order_by(Entity.created_at.desc())).scalars().all()
    latest_by_provider: dict[str, Entity] = {}
    for policy in policies:
        latest_by_provider.setdefault(str(policy.data.get("provider_id")), policy)
    global_used = sum(
        int(p.data.get("_reserved_minor", 0)) + int(p.data.get("_spent_minor", 0))
        for p in latest_by_provider.values()
    )
    if global_used + amount_minor > int(config.get("paid_budget_minor", 0)):
        raise DomainError("budget_exceeded", 409, "Budget payant global du tenant insuffisant.")

    return update_row(row, _reserved_minor=reserved + amount_minor)


def reconcile_provider_budget(session: Session, ctx: AuthContext, provider_id: str, amount_minor: int, outcome: str) -> dict:
    if amount_minor < 0:
        raise DomainError("invalid_request", 422, "Montant de réconciliation invalide.")
    row = _policy_row(session, ctx, provider_id)
    data = dict(row.data)
    reserved = int(data.get("_reserved_minor", 0))
    if amount_minor > reserved:
        raise DomainError("provider_outcome_unknown", 409, "Réserve fournisseur incohérente; réconciliation requise.")
    if outcome == "spent":
        return update_row(
            row,
            _reserved_minor=reserved - amount_minor,
            _spent_minor=int(data.get("_spent_minor", 0)) + amount_minor,
        )
    if outcome == "released":
        return update_row(row, _reserved_minor=reserved - amount_minor)
    if outcome == "unknown":
        return dict(row.data)
    raise DomainError("invalid_request", 422, "Issue de réconciliation inconnue.")
