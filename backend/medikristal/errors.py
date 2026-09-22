from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from fastapi import Request
from fastapi.responses import ORJSONResponse


@dataclass
class DomainError(Exception):
    code: str
    status: int
    detail: str
    title: str = "MediKristal request rejected"
    retryable: bool = False
    field_errors: list[dict] = field(default_factory=list)


def error_response(request: Request, exc: DomainError) -> ORJSONResponse:
    correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
    return ORJSONResponse(
        status_code=exc.status,
        media_type="application/problem+json",
        content={
            "type": f"urn:medikristal:error:{exc.code}",
            "title": exc.title,
            "status": exc.status,
            "code": exc.code,
            "detail": exc.detail,
            "correlation_id": correlation_id,
            "field_errors": exc.field_errors,
            "retryable": exc.retryable,
        },
    )
