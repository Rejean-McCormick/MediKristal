from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = "/tmp/medikristal_pytest.db"
os.environ.setdefault("MEDIKRISTAL_DATABASE_URL", f"sqlite+pysqlite:///{DB_PATH}")
os.environ.setdefault("MEDIKRISTAL_ENV", "test")
os.environ.setdefault("MEDIKRISTAL_ALLOW_TEST_TOKEN", "1")
os.environ.setdefault("MEDIKRISTAL_AUTH_SECRET", "x" * 64)
os.environ.setdefault("MEDIKRISTAL_CONTRACT_DIR", str(ROOT / "contracts"))
os.environ.setdefault("MEDIKRISTAL_FRONTEND_DIR", str(ROOT / "frontend"))

from fastapi.testclient import TestClient
from medikristal.app import app
from medikristal.db import Base, engine


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def signed_token(tenant_id: str, principal_id: str, permissions: list[str], case_grants: list[str] | None = None) -> str:
    payload = {
        "tenant_id": tenant_id,
        "principal_id": principal_id,
        "permissions": permissions,
        "case_grants": case_grants or [],
        "exp": int(time.time()) + 3600,
    }
    pb = _b64(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode())
    sig = _b64(hmac.new(os.environ["MEDIKRISTAL_AUTH_SECRET"].encode(), pb.encode(), hashlib.sha256).digest())
    return pb + "." + sig


@pytest.fixture(autouse=True)
def clean_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def all_headers():
    return {"Authorization": "Bearer test-all"}


@pytest.fixture
def tenant_one():
    return "00000000-0000-4000-8000-000000000001"


@pytest.fixture
def tenant_two():
    return "00000000-0000-4000-8000-000000000099"
