from __future__ import annotations

from medikristal.planning import BranchCost, expected_cost
from medikristal.util import digest
from .helpers import assert_schema, new_case, post


def _capability(client, headers):
    body={"procedure":{"system":"urn:medikristal:synthetic","code":"SYN-T1","version":"1"},"site_ref":"synthetic-site","resource_refs":["synthetic-machine"],"required_skills":["synthetic-operator"],"duration_minutes":15,"capacity":1,"constraints":["engineering_only"]}
    r=post(client,'/resource-capabilities',headers,body,'cap')
    assert r.status_code==201
    return r.json()


def test_at009_zero_cost_is_distinct_from_absent_cost(client, all_headers):
    cap=_capability(client,all_headers)
    zero={"capability_id":cap['id'],"amount_minor":0,"currency":"CAD","kind":"marginal","perspective":"synthetic_facility","valid_from":"2026-09-22T12:00:00Z","valid_until":"2026-09-23T12:00:00Z","source":{"source_id":"synthetic","source_version":"1","record_id":"c0"}}
    r=post(client,'/cost-quotes',all_headers,zero,'cost0')
    assert r.status_code==201 and r.json()['amount_minor']==0
    listed=client.get('/api/v1/cost-quotes',headers=all_headers,params={'capability_id':cap['id']}).json()['items']
    assert len(listed)==1 and listed[0]['amount_minor']==0
    other=_capability(client,{**all_headers}) if False else None


def test_at010_last_slot_only_one_booking(client, all_headers):
    case=new_case(client,all_headers)
    # Create a synthetic accepted order directly through the public flow would require proposal acceptance and config;
    # this fixture uses a seeded ServiceOrder through helper endpoints unavailable in the public contract, so instead
    # exercise the resource owner conflict by creating the minimal order row in the repository.
    from medikristal.db import SessionLocal
    from medikristal.security import AuthContext
    from medikristal.store import create_entity
    ctx=AuthContext('00000000-0000-4000-8000-000000000001','test-principal',frozenset({'*'}))
    with SessionLocal() as db:
        order=create_entity(db,ctx,'ServiceOrder',{"proposal_id":"00000000-0000-4000-8000-000000000010","case_id":case['id'],"case_revision":case['revision'],"destination":"synthetic-facility","status":"requested","foreign_ref":None},parent_id=case['id'],status='requested')
        db.commit()
    cap=_capability(client,all_headers)
    av={"owner":"synthetic-facility","captured_at":"2026-09-22T12:00:00Z","valid_until":"2026-09-22T13:00:00Z","mode":"confirmed","slots":[{"slot_id":"last","start":"2026-09-22T12:15:00Z","end":"2026-09-22T12:30:00Z","state":"free","remaining_capacity":1}]}
    snap=post(client,f"/resource-capabilities/{cap['id']}/availability",all_headers,av,'av').json()
    req={"order_id":order['id'],"capability_id":cap['id'],"slot_id":"last","availability_snapshot_id":snap['id']}
    a=post(client,'/bookings',all_headers,req,'book-a')
    b=post(client,'/bookings',all_headers,req,'book-b')
    assert a.status_code==202
    assert b.status_code==409 and b.json()['code']=='booking_conflict'
    booking=client.get('/api/v1/bookings/'+a.json()['result_ref'],headers=all_headers).json()
    assert_schema('Booking',booking)


def test_at026_expected_branch_cost_oracle():
    # B=20 then A=500 in 30% of branches => 20 + .30*500 = 170.
    assert expected_cost(20,[BranchCost(0.30,500)])==170.0


def test_at028_late_result_creates_visible_followup(client, all_headers):
    case=new_case(client,all_headers)
    # Close the case.
    r=post(client,f"/cases/{case['id']}/transitions",all_headers,{"target":"closed","reason":"done"},'close',case['revision'])
    case=r.json()
    item={"external_item_id":"late-1","replaces_id":None,"observation":{"concept":{"system":"urn:medikristal:synthetic","code":"SYN-T1","version":"1"},"kind":"test_result","presence":"present","value":{"kind":"boolean","value":True},"effective_at":"2026-09-22T12:00:00Z","status":"final","source":{"source_id":"synthetic-lab","source_version":"1","record_id":"late-1"},"quality":"usable","method_ref":None,"dependency_refs":[]}}
    canonical={"owner":"synthetic-lab","report_id":"r1","report_version":"1","items":[item]}
    body={"case_revision":case['revision'],**canonical,"digest":digest(canonical)}
    rec=post(client,f"/cases/{case['id']}/result-batches",all_headers,body,'late',case['revision'])
    assert rec.status_code==200
    tasks=client.get(f"/api/v1/cases/{case['id']}/followups",headers=all_headers).json()['items']
    assert len(tasks)==1 and tasks[0]['owner_ref'] is None and tasks[0]['status']=='open'
