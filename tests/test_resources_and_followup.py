from __future__ import annotations

from datetime import datetime, timedelta, timezone

from medikristal.planning import BranchCost, expected_cost
from medikristal.util import digest
from .helpers import assert_schema, new_case, post


def _future(minutes: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat().replace('+00:00', 'Z')


def _catalog(client, headers, suffix='1'):
    site = post(client, '/sites', headers, {
        'owner': 'synthetic-facility', 'external_id': f'site-{suffix}', 'name': f'Synthetic Site {suffix}',
        'timezone': 'UTC', 'status': 'active'
    }, f'site-{suffix}')
    assert site.status_code == 201, site.text
    site = site.json()
    resource = post(client, '/managed-resources', headers, {
        'site_id': site['id'], 'external_id': f'machine-{suffix}', 'kind': 'equipment',
        'name': f'Synthetic Machine {suffix}', 'status': 'active'
    }, f'resource-{suffix}')
    assert resource.status_code == 201, resource.text
    return site, resource.json()


def _capability(client, headers, suffix='1', capacity=1):
    site, resource = _catalog(client, headers, suffix)
    body = {
        'procedure': {'system': 'urn:medikristal:synthetic', 'code': 'SYN-T1', 'version': '1'},
        'site_ref': site['id'], 'resource_refs': [resource['id']], 'required_skills': ['synthetic-operator'],
        'duration_minutes': 15, 'capacity': capacity, 'constraints': ['engineering_only']
    }
    r = post(client, '/resource-capabilities', headers, body, f'cap-{suffix}')
    assert r.status_code == 201, r.text
    return r.json()


def test_at009_zero_cost_is_distinct_from_absent_cost(client, all_headers):
    cap = _capability(client, all_headers)
    zero = {
        'capability_id': cap['id'], 'amount_minor': 0, 'currency': 'CAD', 'kind': 'marginal',
        'perspective': 'synthetic_facility', 'valid_from': _future(-5), 'valid_until': _future(1440),
        'source': {'source_id': 'synthetic', 'source_version': '1', 'record_id': 'c0'}
    }
    r = post(client, '/cost-quotes', all_headers, zero, 'cost0')
    assert r.status_code == 201 and r.json()['amount_minor'] == 0
    listed = client.get('/api/v1/cost-quotes', headers=all_headers, params={'capability_id': cap['id']}).json()['items']
    assert len(listed) == 1 and listed[0]['amount_minor'] == 0


def test_at010_last_slot_only_one_booking(client, all_headers):
    case = new_case(client, all_headers)
    from medikristal.db import SessionLocal
    from medikristal.security import AuthContext
    from medikristal.store import create_entity
    ctx = AuthContext('00000000-0000-4000-8000-000000000001', 'test-principal', frozenset({'*'}), frozenset({'*'}))
    with SessionLocal() as db:
        order = create_entity(db, ctx, 'ServiceOrder', {
            'proposal_id': '00000000-0000-4000-8000-000000000010', 'case_id': case['id'],
            'case_revision': case['revision'], 'destination': 'synthetic-facility', 'status': 'requested', 'foreign_ref': None
        }, parent_id=case['id'], status='requested')
        db.commit()
    cap = _capability(client, all_headers)
    av = {'owner': 'synthetic-facility', 'captured_at': _future(-1), 'valid_until': _future(60), 'mode': 'confirmed',
          'slots': [{'slot_id': 'last', 'start': _future(15), 'end': _future(30), 'state': 'free', 'remaining_capacity': 1}]}
    snap = post(client, f"/resource-capabilities/{cap['id']}/availability", all_headers, av, 'av').json()
    req = {'order_id': order['id'], 'capability_id': cap['id'], 'slot_id': 'last', 'availability_snapshot_id': snap['id']}
    a = post(client, '/bookings', all_headers, req, 'book-a')
    b = post(client, '/bookings', all_headers, req, 'book-b')
    assert a.status_code == 202, a.text
    assert b.status_code == 409 and b.json()['code'] == 'booking_conflict'
    booking = client.get('/api/v1/bookings/' + a.json()['result_ref'], headers=all_headers).json()
    assert_schema('Booking', booking)


def test_at026_expected_branch_cost_oracle():
    assert expected_cost(20, [BranchCost(0.30, 500)]) == 170.0


def test_at028_late_result_creates_visible_followup(client, all_headers):
    case = new_case(client, all_headers)
    r = post(client, f"/cases/{case['id']}/transitions", all_headers, {'target': 'closed', 'reason': 'done'}, 'close', case['revision'])
    case = r.json()
    item = {'external_item_id': 'late-1', 'replaces_id': None, 'observation': {
        'concept': {'system': 'urn:medikristal:synthetic', 'code': 'SYN-T1', 'version': '1'}, 'kind': 'test_result',
        'presence': 'present', 'value': {'kind': 'boolean', 'value': True}, 'effective_at': _future(-5), 'status': 'final',
        'source': {'source_id': 'synthetic-lab', 'source_version': '1', 'record_id': 'late-1'}, 'quality': 'usable',
        'method_ref': None, 'dependency_refs': []}}
    canonical = {'owner': 'synthetic-lab', 'report_id': 'r1', 'report_version': '1', 'items': [item]}
    body = {'case_revision': case['revision'], **canonical, 'digest': digest(canonical)}
    rec = post(client, f"/cases/{case['id']}/result-batches", all_headers, body, 'late', case['revision'])
    assert rec.status_code == 200, rec.text
    tasks = client.get(f"/api/v1/cases/{case['id']}/followups", headers=all_headers).json()['items']
    assert len(tasks) == 1
    assert tasks[0]['owner_ref'] == 'test-principal'
    assert tasks[0]['status'] == 'assigned'
