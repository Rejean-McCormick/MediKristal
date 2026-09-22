from __future__ import annotations

import csv
import hashlib
import io
from datetime import datetime
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import Blob, Entity
from .errors import DomainError
from .security import AuthContext


CAPABILITY_COLUMNS = [
    "site_external_id", "procedure_system", "procedure_code", "procedure_version",
    "resource_external_id", "duration_minutes", "capacity",
]
PRICE_COLUMNS = [
    "capability_external_id", "amount_minor", "currency", "kind", "perspective",
    "valid_from", "valid_until",
]
PARSER_VERSION = "medikristal-local-catalog-csv/1"
MAPPING_VERSION = "medikristal-local-catalog-map/1"


@dataclass(frozen=True)
class ParsedImport:
    profile: str
    kind: str
    rows: list[dict]
    raw_records: list[dict]
    issues: list[dict]
    extra_columns: list[str]

    @property
    def status(self) -> str:
        return "quarantined" if any(i["severity"] == "error" for i in self.issues) else "completed"


def raw_digest(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(content).hexdigest()


def _parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("timestamp ISO 8601 invalide") from exc
    if parsed.tzinfo is None:
        raise ValueError("timestamp sans fuseau interdit")
    return parsed


def resolve_blob(session: Session, ctx: AuthContext, uploaded_file_ref: str, expected_digest: str) -> Blob:
    if not uploaded_file_ref.startswith("blob:"):
        raise DomainError(
            "unsupported_profile", 422,
            "uploaded_file_ref doit être un identifiant opaque blob:<uuid>; les chemins et URL libres sont interdits.",
        )
    blob_id = uploaded_file_ref[5:]
    row = session.execute(select(Blob).where(Blob.id == blob_id, Blob.tenant_id == ctx.tenant_id)).scalar_one_or_none()
    if row is None:
        raise DomainError("not_found", 404, "Blob de quarantaine introuvable.")
    if row.classification != "quarantine":
        raise DomainError("permission_denied", 403, "Le blob n'est pas classé en quarantaine d'import.")
    calculated = raw_digest(row.content)
    if calculated != row.digest or calculated != expected_digest:
        raise DomainError("artifact_integrity_failed", 422, "Le digest du blob ne correspond pas au contenu stocké.")
    return row


def parse_local_catalog_csv(content: bytes) -> ParsedImport:
    try:
        text = content.decode("utf-8-sig", errors="strict")
    except UnicodeDecodeError as exc:
        return ParsedImport(
            profile="medikristal-local-catalog/1", kind="unknown", rows=[], raw_records=[], extra_columns=[],
            issues=[{"record_ref": "file", "code": "invalid_encoding", "severity": "error", "detail": str(exc)}],
        )
    reader = csv.DictReader(io.StringIO(text, newline=""))
    fields = reader.fieldnames or []
    if "site_external_id" in fields:
        kind, required = "capabilities", CAPABILITY_COLUMNS
    elif "capability_external_id" in fields:
        kind, required = "prices", PRICE_COLUMNS
    else:
        return ParsedImport(
            profile="medikristal-local-catalog/1", kind="unknown", rows=[], raw_records=[], extra_columns=list(fields),
            issues=[{
                "record_ref": "header", "code": "import_schema_mismatch", "severity": "error",
                "detail": "Le profil ne correspond ni au catalogue de capacités ni au catalogue de prix.",
            }],
        )
    missing = [c for c in required if c not in fields]
    if missing:
        return ParsedImport(
            profile="medikristal-local-catalog/1", kind=kind, rows=[], raw_records=[],
            extra_columns=[c for c in fields if c not in required],
            issues=[{
                "record_ref": "header", "code": "import_schema_mismatch", "severity": "error",
                "detail": "Colonnes requises absentes: " + ", ".join(missing),
            }],
        )

    rows: list[dict] = []
    raw_records: list[dict] = []
    issues: list[dict] = []
    for line, source in enumerate(reader, start=2):
        raw_records.append({"line": line, "fields": {k: source.get(k) for k in fields}})
        normalized = {k: (source.get(k) or "").strip() for k in required}
        try:
            if kind == "capabilities":
                for required_text in ("site_external_id", "procedure_system", "procedure_code", "resource_external_id"):
                    if not normalized[required_text]:
                        raise ValueError(f"{required_text} est vide")
                normalized["duration_minutes"] = int(normalized["duration_minutes"])
                normalized["capacity"] = int(normalized["capacity"])
                if normalized["duration_minutes"] <= 0 or normalized["capacity"] <= 0:
                    raise ValueError("duration_minutes et capacity doivent être > 0")
            else:
                for required_text in ("capability_external_id", "currency", "kind", "perspective", "valid_from", "valid_until"):
                    if not normalized[required_text]:
                        raise ValueError(f"{required_text} est vide")
                normalized["amount_minor"] = int(normalized["amount_minor"])
                if normalized["amount_minor"] < 0:
                    raise ValueError("amount_minor doit être >= 0")
                if len(normalized["currency"]) != 3 or not normalized["currency"].isalpha():
                    raise ValueError("currency doit contenir trois lettres")
                normalized["currency"] = normalized["currency"].upper()
                if normalized["kind"] not in {"marginal", "average", "tariff", "patient_out_of_pocket"}:
                    raise ValueError("kind non admis")
                valid_from = _parse_timestamp(normalized["valid_from"])
                valid_until = _parse_timestamp(normalized["valid_until"])
                if valid_until <= valid_from:
                    raise ValueError("valid_until doit être postérieur à valid_from")
            normalized["_raw"] = {k: source.get(k) for k in fields}
            normalized["_line"] = line
            rows.append(normalized)
        except (TypeError, ValueError) as exc:
            issues.append({
                "record_ref": str(line), "code": "invalid_record", "severity": "error", "detail": str(exc),
            })
    for extra in [c for c in fields if c not in required]:
        issues.append({
            "record_ref": "header", "code": "extra_column", "severity": "warning",
            "detail": f"Colonne facultative/inconnue conservée dans le brut: {extra}",
        })
    return ParsedImport(
        profile="medikristal-local-catalog/1", kind=kind, rows=rows, raw_records=raw_records, issues=issues,
        extra_columns=[c for c in fields if c not in required],
    )


def existing_source_snapshot(session: Session, ctx: AuthContext, source_id: str, source_version: str, blob_digest: str) -> Entity | None:
    foreign_key = f"{source_id}:{source_version}:{blob_digest}"
    return session.execute(select(Entity).where(
        Entity.tenant_id == ctx.tenant_id,
        Entity.kind == "SourceSnapshot",
        Entity.foreign_key == foreign_key,
    )).scalars().first()
