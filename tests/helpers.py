from __future__ import annotations

from medikristal.contracts import validator
from medikristal import synthetic as syn


def post(client, path, headers, body, key, match=None):
    h = {**headers, "Idempotency-Key": key}
    if match is not None:
        h["If-Match"] = f'"{match}"'
    return client.post("/api/v1" + path, json=body, headers=h)


def assert_schema(name: str, payload: dict):
    errors = sorted(validator(name).iter_errors(payload), key=lambda e: list(e.absolute_path))
    assert not errors, "\n".join(f"{list(e.absolute_path)}: {e.message}" for e in errors)


def new_case(client, headers, key="case-1"):
    body = {
        "subject_ref": "00000000-0000-4000-8000-000000000003",
        "intended_use": "engineering",
        "language": "fr",
        "synthetic": True,
        "context_refs": [],
    }
    r = post(client, "/cases", headers, body, key)
    assert r.status_code == 201, r.text
    case = r.json()
    r = post(client, f"/cases/{case['id']}/transitions", headers, {"target": "active", "reason": "test"}, key + "-activate", case["revision"])
    assert r.status_code == 200, r.text
    return r.json()


def observation_body(record_id="obs-1", *, value=True, presence="present", kind="test_result"):
    return {
        "concept": {"system": "urn:medikristal:synthetic", "code": "SYN-T1" if kind == "test_result" else "SYN-ALLERGY", "version": "1"},
        "kind": kind,
        "presence": presence,
        "value": {"kind": "boolean", "value": value} if presence == "present" else None,
        "effective_at": "2026-09-22T12:00:00Z",
        "status": "final",
        "source": {"source_id": "synthetic-fixture", "source_version": "1", "record_id": record_id},
        "quality": "usable",
        "method_ref": None,
        "dependency_refs": [],
    }


def evaluate_binary(client, headers, case, key="eval-1"):
    models = client.get("/api/v1/knowledge/models", headers=headers).json()["items"]
    model = next(m for m in models if m["id"] == "synthetic-binary")
    body = {
        "case_revision": case["revision"],
        "knowledge_release": dict(syn.SYN_RELEASE),
        "model_refs": [{"id": model["id"], "version": model["version"], "digest": model["digest"]}],
        "evaluation_time": "2026-09-22T12:00:00Z",
        "intended_use": "engineering",
    }
    r = post(client, f"/cases/{case['id']}/evaluations", headers, body, key, case["revision"])
    assert r.status_code == 202, r.text
    operation = r.json()
    ev = client.get(f"/api/v1/evaluations/{operation['result_ref']}", headers=headers).json()
    return operation, ev
