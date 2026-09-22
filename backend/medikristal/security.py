from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass

from fastapi import Header, Request

from .config import load_settings
from .contracts import permission_for
from .errors import DomainError


settings = load_settings()


@dataclass(frozen=True)
class AuthContext:
    tenant_id: str
    principal_id: str
    permissions: frozenset[str]

    def permits(self, permission: str | None) -> bool:
        if permission is None:
            return True
        return permission in self.permissions or "*" in self.permissions or permission.split(":", 1)[0] + ":*" in self.permissions


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _secret() -> bytes:
    value = settings.auth_secret
    if not value and settings.environment in {"development", "test"}:
        value = "medikristal-local-development-secret-do-not-use-in-production"
    return value.encode("utf-8")


def decode_token(token: str) -> AuthContext:
    if token == "test-all" and settings.allow_test_token:
        return AuthContext(
            tenant_id="00000000-0000-4000-8000-000000000001",
            principal_id="test-principal",
            permissions=frozenset({"*"}),
        )
    try:
        payload_b64, signature_b64 = token.split(".", 1)
        expected = hmac.new(_secret(), payload_b64.encode(), hashlib.sha256).digest()
        signature = _b64decode(signature_b64)
        if not hmac.compare_digest(expected, signature):
            raise ValueError("signature")
        payload = json.loads(_b64decode(payload_b64))
        if payload.get("exp") is not None and int(payload["exp"]) < int(time.time()):
            raise ValueError("expired")
        return AuthContext(
            tenant_id=str(payload["tenant_id"]),
            principal_id=str(payload["principal_id"]),
            permissions=frozenset(str(x) for x in payload.get("permissions", [])),
        )
    except Exception as exc:
        raise DomainError("authentication_required", 401, "Jeton d'accès invalide ou expiré.") from exc


def auth_context(request: Request, authorization: str | None = Header(default=None)) -> AuthContext:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise DomainError("authentication_required", 401, "Authentification bearer requise.")
    ctx = decode_token(authorization[7:].strip())
    request.state.auth = ctx
    return ctx


def authorize(ctx: AuthContext, operation_id: str) -> None:
    permission = permission_for(operation_id)
    if not ctx.permits(permission):
        raise DomainError("permission_denied", 403, "Action non autorisée pour ce principal.")
