from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from medikristal import synthetic as syn
from medikristal.adapters import UnavailableAdapter
from medikristal.config import load_settings
from medikristal.db import SessionLocal
from medikristal.errors import DomainError
from medikristal.provider_budget import reserve_provider_budget
from medikristal.security import AuthContext

from .helpers import assert_schema, new_case, observation_body, post
from .test_integrity_expanded import TENANT, _seed_order
from .test_resources_and_followup import _capability, _future


def _iso(delta_days: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=delta_days)).isoformat().replace('+00:00', 'Z')


def test_evaluation_replay_is_deterministic_and_empty_model_set_abstains(client, all_headers):
    case = new_case(client, all_headers, 'replay-case')
    assert post(client, f"/cases/{case['id']}/observations", all_headers, observation_body('replay-observation'), 'replay-observation', case['revision']).status_code == 200
    case = client.get(f"/api/v1/cases/{case['id']}", headers=all_headers).json()
    model = next(x for x in client.get('/api/v1/knowledge/models', headers=all_headers).json()['items'] if x['id'] == syn.MODEL['id'])
    body = {
        'case_revision': case['revision'], 'knowledge_release': dict(syn.SYN_RELEASE),
        'model_refs': [{k:model[k] for k in ('id','version','digest')}],
        'evaluation_time': '2026-09-22T12:00:00Z', 'intended_use': 'engineering',
    }
    a = post(client, f"/cases/{case['id']}/evaluations", all_headers, body, 'replay-a', case['revision']).json()
    b = post(client, f"/cases/{case['id']}/evaluations", all_headers, body, 'replay-b', case['revision']).json()
    ea = client.get('/api/v1/evaluations/' + a['result_ref'], headers=all_headers).json()
    eb = client.get('/api/v1/evaluations/' + b['result_ref'], headers=all_headers).json()
    assert ea['replay_digest'] == eb['replay_digest']
    assert ea['hypotheses'] == eb['hypotheses']

    empty = {**body, 'model_refs': []}
    op = post(client, f"/cases/{case['id']}/evaluations", all_headers, empty, 'replay-empty', case['revision'])
    assert op.status_code == 202, op.text
    ev = client.get('/api/v1/evaluations/' + op.json()['result_ref'], headers=all_headers).json()
    assert ev['status'] == 'out_of_scope' and ev['hypotheses'] == []
    assert_schema('Evaluation', ev)


def test_unavailable_adapter_never_fakes_partner_success():
    adapter = UnavailableAdapter('fhir_partner')
    with pytest.raises(DomainError) as exc:
        adapter.export({'resourceType':'Bundle'})
    assert exc.value.code == 'capability_unavailable' and exc.value.status == 503


def test_import_rejects_arbitrary_filesystem_reference(client, all_headers):
    source = post(client, '/sources', all_headers, {
        'name':'Local catalog','publisher':'fixture','uri':'urn:fixture:source',
        'source_type':'local_catalog','access':'free','rights':'local_import_only','rights_evidence_ref':'fixture',
    }, 'path-source').json()
    r = post(client, f"/sources/{source['id']}/imports", all_headers, {
        'source_version':'1','uploaded_file_ref':'/etc/passwd','expected_digest':'sha256:' + '0'*64,
    }, 'path-import')
    assert r.status_code == 422 and r.json()['code'] == 'unsupported_profile'


def test_release_selector_filters_models_and_protocols(client, all_headers):
    binary = next(x for x in client.get('/api/v1/knowledge/models', headers=all_headers).json()['items'] if x['id'] == syn.MODEL['id'])
    protocol = client.get('/api/v1/knowledge/protocols', headers=all_headers).json()['items'][0]
    built = post(client, '/knowledge/releases', all_headers, {
        'source_snapshot_refs':[],
        'model_refs':[{k:binary[k] for k in ('id','version','digest')}],
        'protocol_refs':[{k:protocol[k] for k in ('id','version','digest')}],
        'intended_use':'engineering','synthetic':True,
    }, 'selector-build')
    assert built.status_code == 202, built.text
    release_id = built.json()['result_ref']
    manifest = client.get('/api/v1/knowledge/releases/' + release_id, headers=all_headers).json()

    models = client.get('/api/v1/knowledge/models', headers=all_headers, params={'release_id':manifest['release_id']}).json()['items']
    protocols = client.get('/api/v1/knowledge/protocols', headers=all_headers, params={'release_id':manifest['release_id']}).json()['items']
    assert [x['id'] for x in models] == [syn.MODEL['id']]
    assert [x['id'] for x in protocols] == [syn.PROTOCOL['id']]
    assert client.get('/api/v1/knowledge/models', headers=all_headers, params={'release_id':'missing'}).json()['items'] == []


def test_release_admission_policy_digest_is_enforced(client, all_headers):
    bad_policy = {**syn.AUTH_POLICY, 'digest':'sha256:' + 'f'*64}
    r = post(client, '/knowledge/exports', all_headers, {
        'release_ref':dict(syn.SYN_RELEASE),'target':'fhir_knowledge','policy_ref':bad_policy,
    }, 'bad-policy-export')
    assert r.status_code == 422 and r.json()['code'] == 'artifact_integrity_failed'


def test_provider_policy_controls_capability_and_period_change_with_reserve(client, all_headers):
    current = client.get('/api/v1/configuration', headers=all_headers)
    rev = int(current.headers['etag'].strip('"'))
    cfg = current.json()
    cfg.update({
        'mode':'online_extended','network_scope':'internet','provider_allowlist':['provider-a'],
        'paid_budget_minor':1000,'currency':'CAD','intended_use':'engineering','execution_policy':'proposal_only',
    })
    changed = post(client, '/configuration/changes', all_headers, cfg, 'provider-config', rev)
    assert changed.status_code == 200, changed.text
    before = {x['name']:x['state'] for x in client.get('/api/v1/capabilities', headers=all_headers).json()['capabilities']}
    assert before['provider_network'] == 'not_configured'

    policy = {
        'provider_id':'provider-a','enabled':True,'allowed_modes':['online_extended'],'allows_patient_data':False,
        'allowed_purposes':['terminology_lookup'],'budget_minor':500,'currency':'CAD',
        'period_start':_iso(-1),'period_end':_iso(1),'fallback_capability':None,
    }
    created = post(client, '/providers/policies', all_headers, policy, 'provider-policy')
    assert created.status_code == 201, created.text
    assert not any(k.startswith('_') for k in created.json())
    after = {x['name']:x['state'] for x in client.get('/api/v1/capabilities', headers=all_headers).json()['capabilities']}
    assert after['provider_network'] == 'available'

    ctx = AuthContext(TENANT, 'budget-test', frozenset({'*'}), frozenset({'*'}))
    with SessionLocal() as db:
        reserve_provider_budget(db, ctx, 'provider-a', 100, load_settings().configuration_default)
        db.commit()
    usage = client.get('/api/v1/providers/provider-a/usage', headers=all_headers)
    assert usage.status_code == 200 and usage.json()['reserved_minor'] == 100

    moved = {**policy, 'period_start':_iso(2), 'period_end':_iso(3)}
    blocked = post(client, '/providers/policies', all_headers, moved, 'provider-period-change')
    assert blocked.status_code == 409 and blocked.json()['code'] == 'provider_outcome_unknown'


def test_capacity_two_allows_exactly_two_independent_claims(client, all_headers):
    case = new_case(client, all_headers, 'capacity-two-case')
    cap = _capability(client, all_headers, 'capacity-two', capacity=2)
    snapshot = post(client, f"/resource-capabilities/{cap['id']}/availability", all_headers, {
        'owner':'synthetic-facility','captured_at':_future(-1),'valid_until':_future(60),'mode':'confirmed',
        'slots':[{'slot_id':'two','start':_future(15),'end':_future(30),'state':'free','remaining_capacity':2}],
    }, 'capacity-two-availability').json()
    responses = []
    for i in range(3):
        order = _seed_order(case)
        responses.append(post(client, '/bookings', all_headers, {
            'order_id':order['id'],'capability_id':cap['id'],'slot_id':'two','availability_snapshot_id':snapshot['id'],
        }, f'capacity-two-book-{i}'))
    assert [r.status_code for r in responses] == [202, 202, 409]
    assert responses[2].json()['code'] == 'booking_conflict'
