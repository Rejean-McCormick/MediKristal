from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from .errors import DomainError


@dataclass(frozen=True)
class AdapterContext:
    """Non-clinical call context shared by adapter boundaries."""

    tenant_id: str
    principal_id: str
    correlation_id: str
    deadline_ms: int | None = None
    classification: str = "internal"


@runtime_checkable
class TerminologyPort(Protocol):
    def lookup(self, system: str, code: str, version: str) -> dict: ...
    def expand(self, value_set_ref: dict) -> list[dict]: ...
    def translate(self, concept: dict, target_system: str) -> list[dict]: ...
    def validate_code(self, concept: dict) -> dict: ...


@runtime_checkable
class EvidencePort(Protocol):
    def fetch_snapshot(self, source_ref: dict) -> dict: ...
    def list_versions(self, source_id: str) -> list[dict]: ...


@runtime_checkable
class InferencePort(Protocol):
    def validate_model(self, model_ref: dict) -> dict: ...
    def evaluate(self, request: dict) -> dict: ...
    def explain(self, evaluation_ref: str) -> dict: ...


@runtime_checkable
class ProtocolPort(Protocol):
    def validate(self, protocol_ref: dict) -> dict: ...
    def evaluate(self, request: dict) -> dict: ...


@runtime_checkable
class PlanningPort(Protocol):
    def compare_strategies(self, request: dict) -> dict: ...
    def allocate(self, request: dict) -> dict: ...


@runtime_checkable
class FacilityPort(Protocol):
    def list_capabilities(self) -> list[dict]: ...
    def availability(self, capability_ref: str) -> dict: ...
    def hold(self, request: dict) -> dict: ...
    def confirm(self, receipt: dict) -> dict: ...
    def cancel(self, receipt: dict) -> dict: ...
    def reconcile(self, command_ref: str) -> dict: ...


@runtime_checkable
class ResultsPort(Protocol):
    def ingest(self, request: dict) -> dict: ...
    def acknowledge(self, receipt: dict) -> dict: ...
    def reconcile(self, command_ref: str) -> dict: ...


@runtime_checkable
class PublicationPort(Protocol):
    def export(self, request: dict) -> dict: ...
    def verify(self, artifact: dict) -> dict: ...
    def submit(self, artifact: dict) -> dict: ...
    def receipt(self, command_ref: str) -> dict: ...


@runtime_checkable
class ProviderPort(Protocol):
    def estimate_cost(self, request: dict) -> dict: ...
    def invoke(self, request: dict) -> dict: ...
    def reconcile_usage(self, command_ref: str) -> dict: ...


@dataclass
class UnavailableAdapter:
    capability: str

    def __getattr__(self, _name: str):
        def unavailable(*_args: Any, **_kwargs: Any):
            raise DomainError(
                "capability_unavailable",
                503,
                f"Adaptateur {self.capability} non configuré.",
                retryable=False,
            )
        return unavailable


@dataclass(frozen=True)
class LocalSyntheticFacilityAdapter:
    """In-process facility test double for the engineering-only synthetic owner.

    It has no network access and cannot be selected for a non-synthetic owner. Returning a
    receipt here is a local engineering state transition, not evidence of an external booking.
    """

    owner: str

    def __post_init__(self) -> None:
        if not self.owner.startswith("synthetic"):
            raise ValueError("LocalSyntheticFacilityAdapter requires a synthetic owner")

    def list_capabilities(self) -> list[dict]:
        return []

    def availability(self, capability_ref: str) -> dict:
        return {"owner": self.owner, "capability_ref": capability_ref, "mode": "local_synthetic"}

    def hold(self, request: dict) -> dict:
        return {"owner": self.owner, "status": "held", "request_ref": request.get("booking_id")}

    def confirm(self, receipt: dict) -> dict:
        return {"owner": self.owner, "status": "confirmed", "receipt": receipt}

    def cancel(self, receipt: dict) -> dict:
        return {"owner": self.owner, "status": "cancelled", "receipt": receipt}

    def reconcile(self, command_ref: str) -> dict:
        return {"owner": self.owner, "status": "confirmed", "command_ref": command_ref}


def facility_adapter(owner: str) -> FacilityPort:
    if owner.startswith("synthetic"):
        return LocalSyntheticFacilityAdapter(owner)
    return UnavailableAdapter(f"facility:{owner}")  # type: ignore[return-value]
