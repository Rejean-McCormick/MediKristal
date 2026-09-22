from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError

from .config import load_settings
from .errors import DomainError


settings = load_settings()


@lru_cache(maxsize=1)
def domain_schema() -> dict:
    return json.loads((settings.contract_dir / "domain.schema.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def openapi_schema() -> dict:
    return json.loads((settings.contract_dir / "openapi.json").read_text(encoding="utf-8"))


def _schema_for(name: str) -> dict:
    root = domain_schema()
    return {"$schema": root.get("$schema", "https://json-schema.org/draft/2020-12/schema"), "$ref": f"#/$defs/{name}", "$defs": root["$defs"]}


@lru_cache(maxsize=256)
def validator(name: str) -> Draft202012Validator:
    return Draft202012Validator(_schema_for(name), format_checker=FormatChecker())


def validate(name: str, value: dict) -> dict:
    errors = sorted(validator(name).iter_errors(value), key=lambda e: list(e.absolute_path))
    if errors:
        fields = []
        for err in errors[:20]:
            path = "/" + "/".join(str(x) for x in err.absolute_path)
            fields.append({"path": path or "/", "code": err.validator or "invalid"})
        raise DomainError("invalid_request", 422, "Le corps ne respecte pas le contrat.", field_errors=fields)
    return value


def permission_for(operation_id: str) -> str | None:
    for path_item in openapi_schema()["paths"].values():
        for op in path_item.values():
            if isinstance(op, dict) and op.get("operationId") == operation_id:
                return op.get("x-permission")
    return None
