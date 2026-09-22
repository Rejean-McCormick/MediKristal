from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value)).hexdigest()


def uuid4() -> str:
    return str(uuid.uuid4())


def artifact_ref(name: str, version: str = "0.1.0") -> dict:
    return {"id": name, "version": version, "digest": digest({"id": name, "version": version})}
