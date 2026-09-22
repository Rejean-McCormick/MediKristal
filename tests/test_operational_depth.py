from __future__ import annotations

from medikristal import synthetic as syn
from medikristal.db import ReservationClaim, SessionLocal
from sqlalchemy import func, select

from .helpers import assert_schema, evaluate_binary, new_case, observation_body, post
from .test_integrity_expanded import _seed_order
from .test_resources_and_followup import _capability, _future


def _observed_case(client, headers, key: str):
    case = new_case(client, headers, key)
    r = post(client, f"/cases/{case['id']}/observations", headers, observation_body(key+'-obs'), key+'-obs', case['revision'])
    assert r.status_code == 200, r.text
    return client.get(f"/api/v1/cases/{case['id']}", headers=headers).json()


def test_question_and_observation_strategies_do_not_require_machine(client, all_headers):
    case = _observed_case(client, all_headers, 'resource-free')
    _, ev = evaluate_binary(client, all_headers, case, 'resource-free-eval')
    proposals = client.get(f"/api/v1/cases/{case['id']}/proposals", headers=all_headers).json()['items']
    req = {
        'case_id':case['id'],'case_revision':case['revision'],'evaluation_id':ev['id'],
        'proposal_ids':[p['id'] for p in proposals],'resource_snapshot_ids':[],'policy_ref':dict(syn.POLICY),
    }
    op = post(client, '/plans', all_headers, req, 'resource-free-plan')
    assert op.status_code == 202, op.text
    plan = client.get('/api/v1/plans/' + op.json()['result_ref'], headers=all_headers).json()
    by_id = {c['strategy_ref']['id'].split(':',1)[1]:c for c in plan['comparisons']}
    for p in proposals:
        if p['kind'] in {'ask','observe'}:
            assert by_id[p['id']]['admissible'] is True
            assert by_id[p['id']]['criteria'][0]['state'] == 'not_applicable'
        if p['kind'] == 'test':
            assert by_id[p['id']]['admissible'] is False
            assert 'capacity_unavailable' in by_id[p['id']]['reason_codes']


def test_evaluation_is_independent_of_resource_price(client, all_headers):
    case = _observed_case(client, all_headers, 'price-independent')
    _, before = evaluate_binary(client, all_headers, case, 'price-before')
    cap = _capability(client, all_headers, 'price-independent')
    for amount, record in [(10,'low'),(99999,'high')]:
        q = {
            'capability_id':cap['id'],'amount_minor':amount,'currency':'CAD','kind':'marginal','perspective':'facility',
            'valid_from':_future(-5),'valid_until':_future(60),
            'source':{'source_id':'fixture','source_version':'1','record_id':record},
        }
        assert post(client, '/cost-quotes', all_headers, q, 'price-'+record).status_code == 201
    _, after = evaluate_binary(client, all_headers, case, 'price-after')
    assert before['hypotheses'] == after['hypotheses']
    assert before['replay_digest'] == after['replay_digest']


def test_booking_cancel_releases_capacity_for_new_booking(client, all_headers):
    case = new_case(client, all_headers, 'cancel-releases')
    cap = _capability(client, all_headers, 'cancel-releases')
    snap = post(client, f"/resource-capabilities/{cap['id']}/availability", all_headers, {
        'owner':'synthetic-facility','captured_at':_future(-1),'valid_until':_future(60),'mode':'confirmed',
        'slots':[{'slot_id':'reusable','start':_future(15),'end':_future(30),'state':'free','remaining_capacity':1}],
    }, 'cancel-av').json()
    order1 = _seed_order(case)
    req1 = {'order_id':order1['id'],'capability_id':cap['id'],'slot_id':'reusable','availability_snapshot_id':snap['id']}
    first_op = post(client, '/bookings', all_headers, req1, 'cancel-first')
    booking = client.get('/api/v1/bookings/' + first_op.json()['result_ref'], headers=all_headers).json()
    cancelled = post(client, f"/bookings/{booking['id']}/cancellations", all_headers, {'reason':'fixture'}, 'cancel-it', booking['revision'])
    assert cancelled.status_code == 202, cancelled.text
    assert client.get('/api/v1/bookings/' + booking['id'], headers=all_headers).json()['status'] == 'cancelled'
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(ReservationClaim).where(ReservationClaim.booking_id==booking['id'])) == 0
    order2 = _seed_order(case)
    second = post(client, '/bookings', all_headers, {
        'order_id':order2['id'],'capability_id':cap['id'],'slot_id':'reusable','availability_snapshot_id':snap['id'],
    }, 'cancel-second')
    assert second.status_code == 202, second.text


def test_followup_requires_owner_then_completion_proof(client, all_headers):
    case = new_case(client, all_headers, 'follow-lifecycle')
    task = post(client, '/followups', all_headers, {
        'case_id':case['id'],'origin_ref':'fixture:origin','owner_ref':None,'due_at':_future(60),'reason':'fixture',
    }, 'follow-create')
    assert task.status_code == 201, task.text
    task = task.json(); assert task['status'] == 'open'; assert_schema('FollowUpTask', task)
    missing_owner = post(client, f"/followups/{task['id']}/transitions", all_headers, {
        'target':'assigned','owner_ref':None,'completion_ref':None,'reason':'assign',
    }, 'follow-no-owner', task['revision'])
    assert missing_owner.status_code == 422
    assigned = post(client, f"/followups/{task['id']}/transitions", all_headers, {
        'target':'assigned','owner_ref':'professional:fixture','completion_ref':None,'reason':'assign',
    }, 'follow-assign', task['revision'])
    assert assigned.status_code == 200, assigned.text
    missing_proof = post(client, f"/followups/{task['id']}/transitions", all_headers, {
        'target':'completed','owner_ref':'professional:fixture','completion_ref':None,'reason':'done',
    }, 'follow-no-proof', assigned.json()['revision'])
    assert missing_proof.status_code == 422
    complete = post(client, f"/followups/{task['id']}/transitions", all_headers, {
        'target':'completed','owner_ref':'professional:fixture','completion_ref':'fixture:result','reason':'done',
    }, 'follow-complete', assigned.json()['revision'])
    assert complete.status_code == 200 and complete.json()['status'] == 'completed'


def test_workflow_transition_state_machine_and_listing(client, all_headers):
    case = new_case(client, all_headers, 'workflow-machine')
    wf = post(client, '/workflows', all_headers, {
        'case_id':case['id'],'case_revision':case['revision'],'protocol_ref':dict(syn.PROTOCOL),
        'authorization_policy_ref':dict(syn.AUTH_POLICY),'intended_use':'engineering',
    }, 'workflow-create')
    assert wf.status_code == 201, wf.text
    wf = wf.json(); assert wf['status'] == 'ready'; assert_schema('WorkflowRun', wf)
    listed = client.get(f"/api/v1/cases/{case['id']}/workflows", headers=all_headers).json()['items']
    assert [x['id'] for x in listed] == [wf['id']]
    started = post(client, f"/workflows/{wf['id']}/transitions", all_headers, {
        'action':'start','reason':'fixture','case_revision':case['revision'],
    }, 'workflow-start', wf['revision'])
    assert started.status_code == 200 and started.json()['status'] == 'running'
    paused = post(client, f"/workflows/{wf['id']}/transitions", all_headers, {
        'action':'pause','reason':'fixture','case_revision':case['revision'],
    }, 'workflow-pause', started.json()['revision'])
    assert paused.status_code == 200 and paused.json()['status'] == 'paused'
    resumed = post(client, f"/workflows/{wf['id']}/transitions", all_headers, {
        'action':'resume','reason':'fixture','case_revision':case['revision'],
    }, 'workflow-resume', paused.json()['revision'])
    assert resumed.status_code == 200 and resumed.json()['status'] == 'running'
    illegal = post(client, f"/workflows/{wf['id']}/transitions", all_headers, {
        'action':'start','reason':'again','case_revision':case['revision'],
    }, 'workflow-illegal', resumed.json()['revision'])
    assert illegal.status_code == 409 and illegal.json()['code'] == 'workflow_transition_forbidden'


def test_care_plan_revision_is_versioned_and_cross_case_reference_is_rejected(client, all_headers):
    case1 = new_case(client, all_headers, 'care-one')
    task1 = post(client, '/followups', all_headers, {
        'case_id':case1['id'],'origin_ref':'fixture:one','owner_ref':'professional:one','due_at':_future(60),'reason':'fixture',
    }, 'care-follow-one').json()
    plan = post(client, f"/cases/{case1['id']}/care-plans", all_headers, {
        'case_revision':case1['revision'],'treatment_option_ids':[],'followup_task_ids':[task1['id']],'reason':'fixture plan',
    }, 'care-create', case1['revision'])
    assert plan.status_code == 200, plan.text
    plan = plan.json(); assert_schema('CarePlan', plan)
    revised = post(client, f"/care-plans/{plan['id']}/revisions", all_headers, {
        'replacement':{'case_revision':case1['revision'],'treatment_option_ids':[],'followup_task_ids':[task1['id']],'reason':'replacement'},
        'status':'closed','reason':'complete fixture',
    }, 'care-revise', plan['revision'])
    assert revised.status_code == 200 and revised.json()['revision'] == plan['revision'] + 1

    case2 = new_case(client, all_headers, 'care-two')
    task2 = post(client, '/followups', all_headers, {
        'case_id':case2['id'],'origin_ref':'fixture:two','owner_ref':None,'due_at':_future(60),'reason':'fixture',
    }, 'care-follow-two').json()
    cross = post(client, f"/care-plans/{plan['id']}/revisions", all_headers, {
        'replacement':{'case_revision':case1['revision'],'treatment_option_ids':[],'followup_task_ids':[task2['id']],'reason':'bad'},
        'status':'active','reason':'cross case',
    }, 'care-cross', revised.json()['revision'])
    assert cross.status_code == 403 and cross.json()['code'] == 'authorization_scope_mismatch'


def test_mode_switch_recomputes_provider_capability_without_implicit_activation(client, all_headers):
    current = client.get('/api/v1/configuration', headers=all_headers)
    rev = int(current.headers['etag'].strip('"'))
    online_free = {**current.json(), 'mode':'online_free','network_scope':'internet','paid_budget_minor':0}
    r = post(client, '/configuration/changes', all_headers, online_free, 'mode-free', rev)
    assert r.status_code == 200, r.text
    states = {x['name']:x['state'] for x in client.get('/api/v1/capabilities', headers=all_headers).json()['capabilities']}
    assert states['provider_network'] == 'unavailable'

    extended = {**r.json(), 'mode':'online_extended','network_scope':'internet','provider_allowlist':['missing-provider'],'paid_budget_minor':100}
    r2 = post(client, '/configuration/changes', all_headers, extended, 'mode-extended', int(r.headers['etag'].strip('"')))
    assert r2.status_code == 200, r2.text
    states2 = {x['name']:x['state'] for x in client.get('/api/v1/capabilities', headers=all_headers).json()['capabilities']}
    assert states2['provider_network'] == 'not_configured'
