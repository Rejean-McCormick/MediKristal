from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import func, select

from medikristal.db import Entity, ReservationClaim, SessionLocal
from medikristal.worker import expire_holds_once

from .helpers import new_case, observation_body, post
from .test_integrity_expanded import _availability, _book, _capability


ROOT = Path(__file__).resolve().parents[1]


def test_reference_ui_serves_all_surfaces_and_openapi_explorer(client):
    page = client.get('/')
    assert page.status_code == 200
    body = page.text
    for view in ('patient', 'professional', 'admin', 'science', 'ops', 'api'):
        assert f'data-view="{view}"' in body
    assert 'api-operation-list' in body
    js = client.get('/app.js')
    assert js.status_code == 200
    assert "fetch('/openapi.json')" in js.text
    assert "openApiOperations" in js.text
    assert "hardcoded-digest" not in js.text
    assert "request('/knowledge/concepts?q=SYN')" in js.text
    assert '<option>complete</option>' not in body


def test_security_headers_and_database_readiness(client, all_headers):
    ready = client.get('/readyz')
    assert ready.status_code == 200 and ready.json() == {'status': 'ready'}
    response = client.get('/api/v1/capabilities', headers=all_headers)
    assert response.status_code == 200
    assert response.headers['cache-control'] == 'no-store'
    assert response.headers['x-content-type-options'] == 'nosniff'
    assert response.headers['referrer-policy'] == 'no-referrer'
    assert "frame-ancestors 'none'" in response.headers['content-security-policy']


def test_worker_expires_local_hold_and_releases_capacity(client, all_headers):
    case = new_case(client, all_headers, 'expiry-case')
    cap = _capability(client, all_headers, 'expiry')
    snap = _availability(client, all_headers, cap, key='expiry-av')
    booking = _book(client, all_headers, case, cap, snap, 'expiry-book')

    with SessionLocal() as db:
        row = db.execute(select(Entity).where(Entity.kind == 'Booking', Entity.id == booking['id'])).scalar_one()
        data = dict(row.data)
        data['hold_expires_at'] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat().replace('+00:00', 'Z')
        row.data = data
        db.commit()
        assert db.scalar(select(func.count()).select_from(ReservationClaim).where(ReservationClaim.booking_id == booking['id'])) == 1

    assert expire_holds_once() == 1
    refreshed = client.get('/api/v1/bookings/' + booking['id'], headers=all_headers)
    assert refreshed.status_code == 200 and refreshed.json()['status'] == 'expired'
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(ReservationClaim).where(ReservationClaim.booking_id == booking['id'])) == 0


def test_failed_idempotent_command_does_not_poison_retry_key(client, all_headers):
    case = new_case(client, all_headers, 'idem-rollback')
    # First attempt fails after idempotency key acquisition because If-Match is stale.
    first = client.post(
        f"/api/v1/cases/{case['id']}/observations",
        headers={**all_headers, 'Idempotency-Key': 'retry-after-failure', 'If-Match': '"999"'},
        json=observation_body('idem-rollback-1'),
    )
    assert first.status_code == 412

    # Same key is reusable because the failed request transaction, including the key claim,
    # was rolled back. This is required for safe retries after a precondition refresh.
    second = client.post(
        f"/api/v1/cases/{case['id']}/observations",
        headers={**all_headers, 'Idempotency-Key': 'retry-after-failure', 'If-Match': f'"{case["revision"]}"'},
        json=observation_body('idem-rollback-1'),
    )
    assert second.status_code == 200, second.text


def test_idempotency_key_is_a_database_concurrency_gate():
    import threading
    import time

    from medikristal.security import AuthContext
    from medikristal.store import idempotent

    ctx = AuthContext('00000000-0000-4000-8000-000000000001', 'idem-thread', frozenset({'*'}))
    start = threading.Barrier(2)
    count_lock = threading.Lock()
    calls = {'count': 0}
    results: list[tuple[dict, int, str | None]] = []
    errors: list[BaseException] = []

    def action():
        with count_lock:
            calls['count'] += 1
        time.sleep(0.15)
        return {'id': 'winner'}, 201, '1'

    def worker():
        try:
            with SessionLocal() as db:
                start.wait(timeout=2)
                result = idempotent(db, ctx, 'threadedCommand', 'same-key', {'value': 1}, action)
                db.commit()
                results.append(result)
        except BaseException as exc:  # captured for a deterministic assertion below
            errors.append(exc)

    threads = [threading.Thread(target=worker), threading.Thread(target=worker)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)

    assert not errors
    assert all(not thread.is_alive() for thread in threads)
    assert calls['count'] == 1
    assert len(results) == 2 and all(result[0] == {'id': 'winner'} for result in results)


def test_documented_adapter_ports_are_structural_and_swappable():
    from medikristal.adapters import FacilityPort, LocalSyntheticFacilityAdapter, facility_adapter
    from medikristal.errors import DomainError

    local = LocalSyntheticFacilityAdapter('synthetic-facility')
    assert isinstance(local, FacilityPort)
    assert local.confirm({'booking_id': 'b1'})['status'] == 'confirmed'

    replacement = facility_adapter('remote-owner-without-profile')
    try:
        replacement.confirm({'booking_id': 'b2'})
    except DomainError as exc:
        assert exc.code == 'capability_unavailable' and exc.status == 503
    else:
        raise AssertionError('an unconfigured facility adapter must not fabricate success')


def test_signed_pagination_cursor_is_bounded_and_context_bound(client, all_headers, tenant_one):
    from .conftest import signed_token

    for index in range(3):
        new_case(client, all_headers, f'page-case-{index}')

    first = client.get('/api/v1/cases?limit=2', headers=all_headers)
    assert first.status_code == 200, first.text
    assert len(first.json()['items']) == 2
    cursor = first.json()['next_cursor']
    assert isinstance(cursor, str) and cursor

    second = client.get('/api/v1/cases', headers=all_headers, params={'limit': 2, 'cursor': cursor})
    assert second.status_code == 200, second.text
    assert len(second.json()['items']) == 1
    assert second.json()['next_cursor'] is None
    assert {x['id'] for x in first.json()['items']}.isdisjoint({x['id'] for x in second.json()['items']})

    tampered = cursor[:-1] + ('A' if cursor[-1] != 'A' else 'B')
    bad = client.get('/api/v1/cases', headers=all_headers, params={'limit': 2, 'cursor': tampered})
    assert bad.status_code == 422

    other_headers = {'Authorization': 'Bearer ' + signed_token(tenant_one, 'different-principal', ['*'])}
    rebound = client.get('/api/v1/cases', headers=other_headers, params={'limit': 2, 'cursor': cursor})
    assert rebound.status_code == 422


def test_pagination_cursor_cannot_be_reused_with_different_filter_scope(client, all_headers):
    # Synthetic concepts are enough to force a second page with limit=1.
    first = client.get('/api/v1/knowledge/concepts', headers=all_headers, params={'q': 'SYN', 'limit': 1})
    assert first.status_code == 200, first.text
    cursor = first.json()['next_cursor']
    assert cursor

    wrong_scope = client.get('/api/v1/knowledge/concepts', headers=all_headers, params={'q': 'SYN-D1', 'limit': 1, 'cursor': cursor})
    assert wrong_scope.status_code == 422

    missing_required_query = client.get('/api/v1/knowledge/concepts', headers=all_headers)
    assert missing_required_query.status_code == 422


def test_catalog_route_metadata_cannot_be_overridden_by_query_parameters(client, all_headers):
    from medikristal.security import AuthContext
    from medikristal.store import create_entity

    with SessionLocal() as db:
        ctx = AuthContext('00000000-0000-4000-8000-000000000001', 'test-all', frozenset({'*'}))
        create_entity(db, ctx, 'ProviderPolicy', {
            'provider_id': 'hidden-provider-policy',
            'enabled': False,
            'allowed_modes': ['online_extended'],
            'allows_patient_data': False,
            'allowed_purposes': ['terminology_lookup'],
            'budget_minor': 1,
            'currency': 'CAD',
            'period_start': '2026-09-01T00:00:00Z',
            'period_end': '2026-10-01T00:00:00Z',
            'fallback_capability': None,
        }, foreign_key='hidden-provider-policy')
        db.commit()

    # These names used to be default-valued FastAPI parameters on dynamically generated
    # handlers. They must now be ignored rather than changing the entity kind/permission.
    response = client.get('/api/v1/sites', headers=all_headers, params={'_kind': 'ProviderPolicy', '_op': 'getProviderUsage'})
    assert response.status_code == 200, response.text
    assert response.json()['items'] == []


def test_import_persists_run_raw_records_candidates_issues_and_checkpoint(client, all_headers):
    from medikristal.db import Blob, utcnow
    from medikristal.importers import raw_digest
    from medikristal.util import uuid4

    source = post(client, '/sources', all_headers, {
        'name': 'Traceable local catalog',
        'publisher': 'MediKristal test',
        'uri': 'urn:medikristal:local:traceable',
        'source_type': 'local_catalog',
        'access': 'free',
        'rights': 'local_import_only',
        'rights_evidence_ref': 'fixture',
    }, 'trace-source').json()
    content = (
        b'site_external_id,procedure_system,procedure_code,procedure_version,resource_external_id,duration_minutes,capacity,note\n'
        b'site-1,urn:medikristal:synthetic,SYN-T1,1,machine-1,15,1,kept raw\n'
    )
    blob_id = uuid4()
    blob_digest = raw_digest(content)
    with SessionLocal() as db:
        db.add(Blob(id=blob_id, tenant_id=source['tenant_id'], digest=blob_digest, media_type='text/csv', classification='quarantine', content=content, created_at=utcnow()))
        db.commit()

    request = {'source_version': '2026.09', 'uploaded_file_ref': 'blob:' + blob_id, 'expected_digest': blob_digest}
    first = post(client, f"/sources/{source['id']}/imports", all_headers, request, 'trace-import-1')
    replay = post(client, f"/sources/{source['id']}/imports", all_headers, request, 'trace-import-2')
    assert first.status_code == replay.status_code == 202

    with SessionLocal() as db:
        runs = db.execute(select(Entity).where(Entity.kind == 'ImportRun', Entity.parent_id == source['id']).order_by(Entity.created_at)).scalars().all()
        snapshots = db.execute(select(Entity).where(Entity.kind == 'SourceSnapshot', Entity.parent_id == source['id'])).scalars().all()
        assert len(runs) == 2 and all(run.data['status'] == 'reviewed' for run in runs)
        assert all(run.data['checkpoint'] == {'stage': 'reviewed', 'record_index': 1} for run in runs)
        assert len(snapshots) == 1
        snapshot = snapshots[0]
        assert all(run.data['snapshot_id'] == snapshot.id for run in runs)

        raw = db.execute(select(Entity).where(Entity.kind == 'RawRecord', Entity.parent_id == snapshot.id)).scalars().all()
        candidates = db.execute(select(Entity).where(Entity.kind == 'MappingCandidate', Entity.parent_id == snapshot.id)).scalars().all()
        issues = db.execute(select(Entity).where(Entity.kind == 'ImportIssue', Entity.parent_id.in_([run.id for run in runs]))).scalars().all()
        assert len(raw) == 1 and raw[0].data['raw']['note'] == 'kept raw'
        assert raw[0].data['normalized']['capacity'] == 1
        assert len(candidates) == 1 and candidates[0].data['source_record_id'] == raw[0].id
        # The extra-column warning belongs to each import run; immutable records are not duplicated.
        assert len(issues) == 2 and all(issue.data['code'] == 'extra_column' for issue in issues)
