from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = Path(__file__).resolve().parent


def _runtime_path(repository_name: str, packaged_name: str) -> Path:
    repository_path = ROOT / repository_name
    if repository_path.exists():
        return repository_path
    return PACKAGE_ROOT / "_assets" / packaged_name


@dataclass(frozen=True)
class Settings:
    database_url: str = field(default_factory=lambda: os.getenv(
        "MEDIKRISTAL_DATABASE_URL", "postgresql+psycopg://medikristal:medikristal@db:5432/medikristal"
    ))
    auth_secret: str = field(default_factory=lambda: os.getenv("MEDIKRISTAL_AUTH_SECRET", ""))
    environment: str = field(default_factory=lambda: os.getenv("MEDIKRISTAL_ENV", "development"))
    allow_test_token: bool = field(default_factory=lambda: os.getenv("MEDIKRISTAL_ALLOW_TEST_TOKEN", "0") == "1")
    auto_create_schema: bool = field(default_factory=lambda: os.getenv("MEDIKRISTAL_AUTO_CREATE_SCHEMA", "0") == "1")
    contract_dir: Path = field(default_factory=lambda: Path(os.getenv("MEDIKRISTAL_CONTRACT_DIR", _runtime_path("contracts", "contracts"))))
    frontend_dir: Path = field(default_factory=lambda: Path(os.getenv("MEDIKRISTAL_FRONTEND_DIR", _runtime_path("frontend", "frontend"))))
    blob_dir: Path = field(default_factory=lambda: Path(os.getenv("MEDIKRISTAL_BLOB_DIR", "/var/lib/medikristal/blobs")))

    @property
    def configuration_default(self) -> dict:
        raw = os.getenv("MEDIKRISTAL_INITIAL_CONFIGURATION")
        if raw:
            return json.loads(raw)
        return {
            "mode": "offline_free",
            "network_scope": "none",
            "intended_use": "engineering",
            "execution_policy": "proposal_only",
            "provider_allowlist": [],
            "paid_budget_minor": 0,
            "currency": "CAD",
            "local_release_ref": None,
        }


def load_settings() -> Settings:
    settings = Settings()
    if settings.environment not in {"development", "test"} and len(settings.auth_secret) < 32:
        raise RuntimeError("MEDIKRISTAL_AUTH_SECRET must contain at least 32 characters outside development/test")
    return settings
