from __future__ import annotations

from medikristal.db import Blob, SessionLocal, utcnow
from medikristal.importers import raw_digest
from medikristal.security import AuthContext
from medikristal.store import create_entity
from medikristal.util import uuid4

from .helpers import new_case, observation_body, post
from .test_resources_and_followup import _capability, _future

TENANT = "00000000-0000-4000-8000-000000000001"


def test_observations_are_paginated_in_clinical_effective_order(client, all_headers):
    case = new_case(client, all_headers, "clinical-order-case")
    late = observation_body("clinical-order-late")
    late["effective_at"] = "2026-09-22T14:00:00Z"
    r = post(client, f"/cases/{case['id']}/observations", all_headers, late, "clinical-order-late", case["revision"])
    assert r.status_code == 200, r.text
    case = client.get(f"/api/v1/cases/{case['id']}", headers=all_headers).json()
    early = observation_body("clinical-order-early")
    early["effective_at"] = "2026-09-22T10:00:00Z"
    r = post(client, f"/cases/{case['id']}/observations", all_headers, early, "clinical-order-early", case["revision"])
    assert r.status_code == 200, r.text

    page = client.get(f"/api/v1/cases/{case['id']}/observations", headers=all_headers, params={"limit": 1}).json()
    assert page["items"][0]["effective_at"] == "2026-09-22T10:00:00Z"
    assert page["next_cursor"]
    page2 = client.get(
        f"/api/v1/cases/{case['id']}/observations", headers=all_headers,
        params={"limit": 1, "cursor": page["next_cursor"]},
    ).json()
    assert page2["items"][0]["effective_at"] == "2026-09-22T14:00:00Z"


def test_availability_rejects_slots_outside_snapshot_and_impossible_state_capacity(client, all_headers):
    cap = _capability(client, all_headers, "availability-guard")
    outside = {
        "owner": "synthetic-facility", "captured_at": _future(-1), "valid_until": _future(20), "mode": "confirmed",
        "slots": [{"slot_id": "outside", "start": _future(10), "end": _future(30), "state": "free", "remaining_capacity": 1}],
    }
    r = post(client, f"/resource-capabilities/{cap['id']}/availability", all_headers, outside, "availability-outside")
    assert r.status_code == 422 and r.json()["code"] == "invalid_request"

    impossible = {
        "owner": "synthetic-facility", "captured_at": _future(-1), "valid_until": _future(60), "mode": "confirmed",
        "slots": [{"slot_id": "booked", "start": _future(10), "end": _future(20), "state": "booked", "remaining_capacity": 1}],
    }
    r = post(client, f"/resource-capabilities/{cap['id']}/availability", all_headers, impossible, "availability-impossible")
    assert r.status_code == 422 and r.json()["code"] == "invalid_request"


def test_booking_rejects_capacity_for_different_ordered_procedure(client, all_headers):
    case = new_case(client, all_headers, "booking-procedure-case")
    ctx = AuthContext(TENANT, "test-principal", frozenset({"*"}), frozenset({"*"}))
    with SessionLocal() as db:
        proposal = create_entity(db, ctx, "ActionProposal", {
            "case_id": case["id"], "case_revision": case["revision"], "evaluation_id": uuid4(),
            "protocol_ref": {"id": "synthetic-protocol", "version": "0.1.0", "digest": "sha256:" + "b" * 64},
            "preconditions": [], "evidence_refs": [], "status": "accepted", "kind": "test",
            "target": {"system": "urn:medikristal:synthetic", "code": "SYN-OTHER", "version": "1"},
            "reason_codes": ["fixture"], "expires_at": _future(60),
        }, parent_id=case["id"], status="accepted")
        order = create_entity(db, ctx, "ServiceOrder", {
            "proposal_id": proposal["id"], "case_id": case["id"], "case_revision": case["revision"],
            "destination": "synthetic-facility", "status": "requested", "foreign_ref": None,
        }, parent_id=case["id"], status="requested")
        db.commit()

    cap = _capability(client, all_headers, "booking-procedure-cap")
    availability = {
        "owner": "synthetic-facility", "captured_at": _future(-1), "valid_until": _future(60), "mode": "confirmed",
        "slots": [{"slot_id": "different-procedure", "start": _future(10), "end": _future(20), "state": "free", "remaining_capacity": 1}],
    }
    snap = post(client, f"/resource-capabilities/{cap['id']}/availability", all_headers, availability, "booking-procedure-av").json()
    r = post(client, "/bookings", all_headers, {
        "order_id": order["id"], "capability_id": cap["id"], "slot_id": "different-procedure", "availability_snapshot_id": snap["id"],
    }, "booking-procedure-mismatch")
    assert r.status_code == 403 and r.json()["code"] == "authorization_scope_mismatch"


def test_price_import_rejects_invalid_interval_before_creating_snapshot(client, all_headers):
    source = post(client, "/sources", all_headers, {
        "name": "Bad price fixture", "publisher": "MediKristal test", "uri": "urn:medikristal:local:bad-price",
        "source_type": "local_catalog", "access": "free", "rights": "local_import_only", "rights_evidence_ref": "fixture",
    }, "bad-price-source").json()
    content = (
        b"capability_external_id,amount_minor,currency,kind,perspective,valid_from,valid_until\n"
        b"cap-1,100,CAD,marginal,facility,2026-09-23T00:00:00Z,2026-09-22T00:00:00Z\n"
    )
    blob_id = uuid4()
    dgst = raw_digest(content)
    with SessionLocal() as db:
        db.add(Blob(id=blob_id, tenant_id=TENANT, digest=dgst, media_type="text/csv", classification="quarantine", content=content, created_at=utcnow()))
        db.commit()
    r = post(client, f"/sources/{source['id']}/imports", all_headers, {
        "source_version": "prices-bad-1", "uploaded_file_ref": "blob:" + blob_id, "expected_digest": dgst,
    }, "bad-price-import")
    assert r.status_code == 202, r.text
    report = client.get(f"/api/v1/imports/{r.json()['id']}/report", headers=all_headers).json()
    assert report["status"] == "quarantined"
    assert any(issue["code"] == "invalid_record" for issue in report["issues"])


def test_worker_claim_rolls_back_if_local_effect_fails(client, all_headers, monkeypatch):
    from sqlalchemy import func, select
    from medikristal import worker
    from medikristal.db import InboxEvent, OutboxEvent, SessionLocal

    new_case(client, all_headers, "worker-effect-failure")
    with SessionLocal() as db:
        event = db.execute(select(OutboxEvent).order_by(OutboxEvent.occurred_at, OutboxEvent.event_id)).scalars().first()
        assert event is not None
        event_id = event.event_id

    def explode(_session, _row):
        raise RuntimeError("synthetic projection failure")

    monkeypatch.setattr(worker, "_handle_local_event", explode)
    import pytest
    with pytest.raises(RuntimeError, match="synthetic projection failure"):
        worker.drain_once(limit=1)

    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(InboxEvent).where(InboxEvent.event_id == event_id)) == 0
        row = db.get(OutboxEvent, event_id)
        assert row is not None and row.delivered is False

    monkeypatch.setattr(worker, "_handle_local_event", lambda _session, _row: None)
    assert worker.drain_once(limit=1) == 1
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(InboxEvent).where(InboxEvent.event_id == event_id)) == 1
        row = db.get(OutboxEvent, event_id)
        assert row is not None and row.delivered is True


def test_concurrent_booking_requests_cannot_overbook_last_capacity(client, all_headers):
    import threading
    from medikristal.db import SessionLocal
    from medikristal.security import AuthContext
    from medikristal.store import create_entity
    from .test_resources_and_followup import _capability, _future

    case = new_case(client, all_headers, "concurrent-last-slot")
    ctx = AuthContext(
        "00000000-0000-4000-8000-000000000001",
        "test-principal",
        frozenset({"*"}),
        frozenset({"*"}),
    )
    with SessionLocal() as db:
        order = create_entity(db, ctx, "ServiceOrder", {
            "proposal_id": "00000000-0000-4000-8000-000000000010",
            "case_id": case["id"], "case_revision": case["revision"],
            "destination": "synthetic-facility", "status": "requested", "foreign_ref": None,
        }, parent_id=case["id"], status="requested")
        db.commit()

    cap = _capability(client, all_headers, "concurrent", capacity=1)
    snapshot = post(client, f"/resource-capabilities/{cap['id']}/availability", all_headers, {
        "owner": "synthetic-facility", "captured_at": _future(-1), "valid_until": _future(60), "mode": "confirmed",
        "slots": [{"slot_id": "only", "start": _future(15), "end": _future(30), "state": "free", "remaining_capacity": 1}],
    }, "concurrent-availability").json()
    request_body = {
        "order_id": order["id"], "capability_id": cap["id"], "slot_id": "only",
        "availability_snapshot_id": snapshot["id"],
    }

    barrier = threading.Barrier(2)
    outcomes: list[tuple[int, str | None]] = []
    errors: list[BaseException] = []
    lock = threading.Lock()

    def contender(key: str) -> None:
        try:
            barrier.wait(timeout=2)
            response = client.post(
                "/api/v1/bookings",
                headers={**all_headers, "Idempotency-Key": key},
                json=request_body,
            )
            code = response.json().get("code") if response.headers.get("content-type", "").startswith("application/problem+json") else None
            with lock:
                outcomes.append((response.status_code, code))
        except BaseException as exc:
            with lock:
                errors.append(exc)

    threads = [threading.Thread(target=contender, args=(f"concurrent-book-{i}",)) for i in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)

    assert not errors
    assert all(not thread.is_alive() for thread in threads)
    assert sorted(status for status, _ in outcomes) == [202, 409]
    assert [code for status, code in outcomes if status == 409] == ["booking_conflict"]


def test_configuration_rejects_malformed_if_match_as_domain_error(client, all_headers):
    current = client.get("/api/v1/configuration", headers=all_headers)
    assert current.status_code == 200
    response = client.post(
        "/api/v1/configuration/changes",
        headers={**all_headers, "Idempotency-Key": "bad-config-etag", "If-Match": "not-an-etag"},
        json=current.json(),
    )
    assert response.status_code == 412
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "precondition_failed"


def test_configuration_cannot_bypass_release_activation(client, all_headers):
    current = client.get("/api/v1/configuration", headers=all_headers)
    assert current.status_code == 200
    body = current.json()
    body["local_release_ref"] = {"id": "forged-release", "version": "1", "digest": "sha256:" + "a" * 64}
    response = client.post(
        "/api/v1/configuration/changes",
        headers={**all_headers, "Idempotency-Key": "forged-local-release", "If-Match": current.headers["etag"]},
        json=body,
    )
    assert response.status_code == 409
    assert response.json()["code"] == "workflow_transition_forbidden"


def test_framework_validation_errors_use_problem_json_contract(client, all_headers):
    response = client.get("/api/v1/knowledge/concepts", headers=all_headers)
    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    payload = response.json()
    assert payload["code"] == "invalid_request"
    assert any(item["path"] == "query.q" for item in payload["field_errors"])

    bad_limit = client.get("/api/v1/cases", headers=all_headers, params={"limit": 0})
    assert bad_limit.status_code == 422
    assert bad_limit.headers["content-type"].startswith("application/problem+json")
    assert any(item["path"] == "query.limit" for item in bad_limit.json()["field_errors"])


def test_mutating_catalog_command_emits_one_durable_event_on_idempotent_replay(client, all_headers):
    from sqlalchemy import func, select
    from medikristal.db import OutboxEvent, SessionLocal

    body = {
        "owner": "synthetic-facility", "external_id": "durable-site",
        "name": "Durable Site", "timezone": "UTC", "status": "active",
    }
    first = post(client, "/sites", all_headers, body, "durable-site-create")
    replay = post(client, "/sites", all_headers, body, "durable-site-create")
    assert first.status_code == replay.status_code == 201
    assert first.json()["id"] == replay.json()["id"]

    with SessionLocal() as db:
        count = db.scalar(select(func.count()).select_from(OutboxEvent).where(
            OutboxEvent.event_type == "medikristal.catalog.changed.v1",
            OutboxEvent.aggregate_type == "Site",
            OutboxEvent.aggregate_id == first.json()["id"],
        ))
        assert count == 1


def test_result_report_exact_replay_returns_original_receipt_after_case_advances(client, all_headers):
    from medikristal.util import digest
    from .test_resources_and_followup import _future

    case = new_case(client, all_headers, "result-replay-case")
    item = {
        "external_item_id": "replay-result-1", "replaces_id": None,
        "observation": {
            "concept": {"system": "urn:medikristal:synthetic", "code": "SYN-T1", "version": "1"},
            "kind": "test_result", "presence": "present", "value": {"kind": "boolean", "value": True},
            "effective_at": _future(-5), "status": "final",
            "source": {"source_id": "synthetic-lab", "source_version": "1", "record_id": "replay-result-1"},
            "quality": "usable", "method_ref": None, "dependency_refs": [],
        },
    }
    canonical = {"owner": "synthetic-lab", "report_id": "replay-report", "report_version": "1", "items": [item]}
    body = {"case_revision": case["revision"], **canonical, "digest": digest(canonical)}
    first = post(client, f"/cases/{case['id']}/result-batches", all_headers, body, "result-replay-first", case["revision"])
    assert first.status_code == 200, first.text
    receipt = first.json()

    advanced = client.get(f"/api/v1/cases/{case['id']}", headers=all_headers).json()
    extra = post(client, f"/cases/{case['id']}/observations", all_headers, observation_body("after-result"), "after-result", advanced["revision"])
    assert extra.status_code == 200, extra.text

    replay = post(client, f"/cases/{case['id']}/result-batches", all_headers, body, "result-replay-second", case["revision"])
    assert replay.status_code == 200, replay.text
    assert replay.json()["id"] == receipt["id"]
    assert replay.json()["digest"] == receipt["digest"]
