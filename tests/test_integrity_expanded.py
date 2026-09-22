from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from medikristal import synthetic as syn
from medikristal.config import load_settings
from medikristal.db import Blob, ConfigurationState, Entity, EntityRevision, InboxEvent, OutboxEvent, ReservationClaim, SessionLocal, utcnow
from medikristal.errors import DomainError
from medikristal.importers import raw_digest
from medikristal.provider_budget import reserve_provider_budget
from medikristal.security import AuthContext
from medikristal.store import create_entity, get_configuration
from medikristal.util import digest, uuid4
from medikristal.worker import drain_once

from .conftest import signed_token
from .helpers import assert_schema, evaluate_binary, new_case, observation_body, post
from .test_resources_and_followup import _capability, _catalog, _future

TENANT = '00000000-0000-4000-8000-000000000001'


def _auth(token: str) -> dict:
    return {'Authorization': 'Bearer ' + token}


def _seed_order(case: dict, *, principal='test-principal') -> dict:
    ctx = AuthContext(TENANT, principal, frozenset({'*'}), frozenset({'*'}))
    with SessionLocal() as db:
        order = create_entity(db, ctx, 'ServiceOrder', {
            'proposal_id': '00000000-0000-4000-8000-000000000010', 'case_id': case['id'],
            'case_revision': case['revision'], 'destination': 'synthetic-facility', 'status': 'requested', 'foreign_ref': None,
        }, parent_id=case['id'], status='requested')
        db.commit()
        return order


def _availability(client, headers, cap: dict, owner='synthetic-facility', key='av') -> dict:
    body = {'owner': owner, 'captured_at': _future(-1), 'valid_until': _future(60), 'mode': 'confirmed',
            'slots': [{'slot_id': 'slot-1', 'start': _future(15), 'end': _future(30), 'state': 'free', 'remaining_capacity': 1}]}
    r = post(client, f"/resource-capabilities/{cap['id']}/availability", headers, body, key)
    assert r.status_code == 201, r.text
    return r.json()


def _book(client, headers, case, cap, snap, key='book'):
    order = _seed_order(case)
    r = post(client, '/bookings', headers, {
        'order_id': order['id'], 'capability_id': cap['id'], 'slot_id': 'slot-1', 'availability_snapshot_id': snap['id'],
    }, key)
    assert r.status_code == 202, r.text
    return client.get('/api/v1/bookings/' + r.json()['result_ref'], headers=headers).json()


def test_response_contracts_for_bundled_knowledge(client, all_headers):
    caps = client.get('/api/v1/capabilities', headers=all_headers).json()
    assert_schema('Capabilities', caps)
    states = {x['name']: x['state'] for x in caps['capabilities']}
    assert states['fhir_partner'] == states['kristal_export'] == 'not_configured'
    for schema, path in [('ModelManifest','/knowledge/models'), ('ProtocolManifest','/knowledge/protocols'), ('EvidenceEstimate','/knowledge/evidence'), ('Assertion','/knowledge/assertions')]:
        response = client.get('/api/v1' + path, headers=all_headers)
        assert response.status_code == 200, response.text
        for item in response.json()['items']:
            assert_schema(schema, item)


def test_case_grant_is_distinct_from_operation_permission(client, tenant_one):
    creator = _auth(signed_token(tenant_one, 'patient-1', ['cases:create','cases:read','cases:update']))
    case = new_case(client, creator, 'grant-case')

    professional = _auth(signed_token(tenant_one, 'professional-1', ['cases:read'], [case['id']]))
    assert client.get(f"/api/v1/cases/{case['id']}", headers=professional).status_code == 200

    researcher = _auth(signed_token(tenant_one, 'researcher-1', ['cases:read']))
    hidden = client.get(f"/api/v1/cases/{case['id']}", headers=researcher)
    assert hidden.status_code == 404 and hidden.json()['code'] == 'not_found'
    assert client.get('/api/v1/cases', headers=researcher).json()['items'] == []

    resource_admin = _auth(signed_token(tenant_one, 'resource-admin', ['resources:admin','resources:read']))
    assert client.get(f"/api/v1/cases/{case['id']}", headers=resource_admin).status_code == 403


def test_entity_revision_history_is_append_only(client, all_headers):
    case = new_case(client, all_headers, 'history-case')
    obs = post(client, f"/cases/{case['id']}/observations", all_headers, observation_body('history-obs'), 'history-obs', case['revision']).json()
    amendment = {'reason': 'correction', 'replacement': observation_body('history-obs-v2', value=False)}
    r = post(client, f"/observations/{obs['id']}/amendments", all_headers, amendment, 'history-amend', obs['revision'])
    assert r.status_code == 200, r.text
    with SessionLocal() as db:
        revisions = db.execute(select(EntityRevision).where(EntityRevision.kind=='Observation', EntityRevision.entity_id==obs['id']).order_by(EntityRevision.revision)).scalars().all()
        assert [x.revision for x in revisions] == [1,2]
        assert revisions[0].data['status'] == 'final'
        assert revisions[1].data['status'] == 'amended'


def test_import_quarantine_retry_and_version_conflict(client, all_headers):
    source_body = {'name':'Local synthetic catalog','publisher':'MediKristal test','uri':'urn:medikristal:local:test',
                   'source_type':'local_catalog','access':'free','rights':'local_import_only','rights_evidence_ref':'fixture'}
    source = post(client, '/sources', all_headers, source_body, 'source-local').json()

    bad = b'site_external_id,procedure_system\nsite-1,urn:medikristal:synthetic\n'
    good = (b'site_external_id,procedure_system,procedure_code,procedure_version,resource_external_id,duration_minutes,capacity\n'
            b'site-1,urn:medikristal:synthetic,SYN-T1,1,machine-1,15,1\n')

    def stage(content: bytes) -> tuple[str,str]:
        d = raw_digest(content); bid = uuid4()
        with SessionLocal() as db:
            db.add(Blob(id=bid, tenant_id=TENANT, digest=d, media_type='text/csv', classification='quarantine', content=content, created_at=utcnow()))
            db.commit()
        return 'blob:' + bid, d

    bad_ref, bad_digest = stage(bad)
    op_bad = post(client, f"/sources/{source['id']}/imports", all_headers,
                  {'source_version':'bad-1','uploaded_file_ref':bad_ref,'expected_digest':bad_digest}, 'import-bad')
    assert op_bad.status_code == 202, op_bad.text
    report_bad = client.get(f"/api/v1/imports/{op_bad.json()['id']}/report", headers=all_headers).json()
    assert report_bad['status'] == 'quarantined' and report_bad['artifact_ref'] is None

    good_ref, good_digest = stage(good)
    req = {'source_version':'1','uploaded_file_ref':good_ref,'expected_digest':good_digest}
    op1 = post(client, f"/sources/{source['id']}/imports", all_headers, req, 'import-good-1')
    op2 = post(client, f"/sources/{source['id']}/imports", all_headers, req, 'import-good-2')
    assert op1.status_code == op2.status_code == 202
    r1 = client.get(f"/api/v1/imports/{op1.json()['id']}/report", headers=all_headers).json()
    r2 = client.get(f"/api/v1/imports/{op2.json()['id']}/report", headers=all_headers).json()
    assert r1['artifact_ref'] == r2['artifact_ref']
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Entity).where(Entity.kind=='SourceSnapshot', Entity.parent_id==source['id'])) == 1

    changed = good.replace(b',15,1\n', b',20,1\n')
    changed_ref, changed_digest = stage(changed)
    conflict = post(client, f"/sources/{source['id']}/imports", all_headers,
                    {'source_version':'1','uploaded_file_ref':changed_ref,'expected_digest':changed_digest}, 'import-conflict')
    assert conflict.status_code == 409 and conflict.json()['code'] == 'source_version_conflict'


def test_release_publish_activate_revoke_invalidates_execution(client, all_headers):
    model = client.get('/api/v1/knowledge/models', headers=all_headers).json()['items'][0]
    proto = client.get('/api/v1/knowledge/protocols', headers=all_headers).json()['items'][0]
    build = post(client, '/knowledge/releases', all_headers, {
        'source_snapshot_refs': [], 'model_refs': [{k:model[k] for k in ('id','version','digest')}],
        'protocol_refs': [{k:proto[k] for k in ('id','version','digest')}], 'intended_use':'engineering', 'synthetic':True,
    }, 'release-build')
    assert build.status_code == 202, build.text
    release_entity_id = build.json()['result_ref']
    candidate = client.get('/api/v1/knowledge/releases/' + release_entity_id, headers=all_headers).json()
    assert candidate['status'] == 'candidate'

    decision = {'verdict':'publish','reason':'synthetic qualification','review_refs':[],'policy_ref':dict(syn.AUTH_POLICY)}
    pub = post(client, f'/knowledge/releases/{release_entity_id}/decisions', all_headers, decision, 'release-publish')
    assert pub.status_code == 202, pub.text
    published = client.get('/api/v1/knowledge/releases/' + release_entity_id, headers=all_headers).json()
    release_ref = {'id':published['release_id'],'version':published['version'],'digest':published['release_id']}
    activation = post(client, '/knowledge/activations', all_headers,
                      {'release_ref':release_ref,'policy_ref':dict(syn.AUTH_POLICY),'reason':'activate fixture'}, 'release-activate')
    assert activation.status_code == 202, activation.text

    case = new_case(client, all_headers, 'release-case')
    post(client, f"/cases/{case['id']}/observations", all_headers, observation_body('release-obs'), 'release-obs', case['revision'])
    case = client.get(f"/api/v1/cases/{case['id']}", headers=all_headers).json()
    eval_body = {'case_revision':case['revision'],'knowledge_release':release_ref,
                 'model_refs':[{k:model[k] for k in ('id','version','digest')}], 'evaluation_time':_future(-1),'intended_use':'engineering'}
    ev_op = post(client, f"/cases/{case['id']}/evaluations", all_headers, eval_body, 'release-eval', case['revision'])
    assert ev_op.status_code == 202, ev_op.text
    ev_id = ev_op.json()['result_ref']

    revoke = post(client, f'/knowledge/releases/{release_entity_id}/decisions', all_headers,
                  {'verdict':'revoke','reason':'fixture revoked','review_refs':[],'policy_ref':dict(syn.AUTH_POLICY)}, 'release-revoke')
    assert revoke.status_code == 202, revoke.text
    assert client.get('/api/v1/evaluations/' + ev_id, headers=all_headers).json()['stale'] is True
    rejected = post(client, f"/cases/{case['id']}/evaluations", all_headers, eval_body, 'release-eval-after-revoke', case['revision'])
    assert rejected.status_code == 409 and rejected.json()['code'] == 'release_not_admitted'
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Entity).where(Entity.kind=='ImpactAnalysis')) == 1


def test_worker_inbox_deduplicates_replayed_event(client, all_headers):
    new_case(client, all_headers, 'worker-case')
    with SessionLocal() as db:
        event = db.execute(select(OutboxEvent).order_by(OutboxEvent.occurred_at)).scalars().first()
        assert event is not None and event.delivered is False
        event_id = event.event_id
    assert drain_once() >= 1
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(InboxEvent).where(InboxEvent.event_id==event_id)) == 1
        row = db.get(OutboxEvent, event_id); row.delivered = False; db.commit()
    assert drain_once() >= 1
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(InboxEvent).where(InboxEvent.event_id==event_id)) == 1


def test_remote_booking_stays_reconciling_and_keeps_claim(client, all_headers):
    case = new_case(client, all_headers, 'remote-book-case')
    cap = _capability(client, all_headers, 'remote')
    snap = _availability(client, all_headers, cap, owner='remote-facility', key='remote-av')
    booking = _book(client, all_headers, case, cap, snap, 'remote-book')
    op = post(client, f"/bookings/{booking['id']}/confirmations", all_headers, {'reason':'confirm'}, 'remote-confirm', booking['revision'])
    assert op.status_code == 202, op.text
    assert op.json()['status'] == 'reconciling' and op.json()['error_code'] == 'provider_outcome_unknown'
    current = client.get('/api/v1/bookings/' + booking['id'], headers=all_headers).json()
    assert current['status'] == 'reconciling'
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(ReservationClaim).where(ReservationClaim.booking_id==booking['id'])) == 1


def test_retiring_reserved_resource_preserves_booking_and_opens_impact(client, all_headers):
    case = new_case(client, all_headers, 'retire-case')
    site, resource = _catalog(client, all_headers, 'retire')
    cap_body = {'procedure':{'system':'urn:medikristal:synthetic','code':'SYN-T1','version':'1'}, 'site_ref':site['id'],
                'resource_refs':[resource['id']], 'required_skills':['operator'], 'duration_minutes':15,'capacity':1,'constraints':['engineering_only']}
    cap = post(client, '/resource-capabilities', all_headers, cap_body, 'retire-cap').json()
    snap = _availability(client, all_headers, cap, key='retire-av')
    booking = _book(client, all_headers, case, cap, snap, 'retire-book')

    replacement = {'site_id':site['id'],'external_id':resource['external_id'],'kind':resource['kind'],'name':resource['name'],'status':'unavailable'}
    revised = post(client, f"/managed-resources/{resource['id']}/revisions", all_headers,
                   {'replacement':replacement,'reason':'maintenance'}, 'retire-resource', resource['revision'])
    assert revised.status_code == 200, revised.text
    assert client.get('/api/v1/bookings/' + booking['id'], headers=all_headers).json()['status'] == 'held'
    with SessionLocal() as db:
        impact = db.execute(select(Entity).where(Entity.kind=='ImpactAnalysis', Entity.data['subject_id'].as_string()==booking['id'])).scalars().first()
        assert impact is not None and impact.data['status'] == 'open'
        queued = db.execute(select(Entity).where(Entity.kind=='Operation', Entity.data['kind'].as_string()=='replan_booking')).scalars().first()
        assert queued is not None and queued.data['status'] == 'queued'


def test_tenant_paid_budget_is_global_across_providers():
    ctx = AuthContext(TENANT, 'budget-principal', frozenset({'*'}))
    now = datetime.now(timezone.utc)
    start=(now-timedelta(days=1)).isoformat().replace('+00:00','Z'); end=(now+timedelta(days=1)).isoformat().replace('+00:00','Z')
    with SessionLocal() as db:
        cfg,_ = get_configuration(db,ctx,load_settings().configuration_default)
        cfg.update({'mode':'online_extended','network_scope':'internet','paid_budget_minor':100,'provider_allowlist':['p1','p2'],'currency':'CAD'})
        state=db.get(ConfigurationState,TENANT); state.data=cfg
        for pid in ('p1','p2'):
            create_entity(db,ctx,'ProviderPolicy',{'provider_id':pid,'enabled':True,'allowed_modes':['online_extended'],'allows_patient_data':False,
                'allowed_purposes':['terminology_lookup'],'budget_minor':100,'currency':'CAD','period_start':start,'period_end':end,'fallback_capability':None},foreign_key=pid)
        db.commit()
    with SessionLocal() as db:
        reserve_provider_budget(db,ctx,'p1',80,load_settings().configuration_default); db.commit()
    with SessionLocal() as db:
        try:
            reserve_provider_budget(db,ctx,'p2',30,load_settings().configuration_default)
        except DomainError as exc:
            assert exc.code == 'budget_exceeded'
        else:
            raise AssertionError('tenant budget must cap the aggregate of provider reservations')


def test_procedure_catalog_rejects_component_cycle(client, all_headers):
    a={'system':'urn:medikristal:test-procedure','code':'A','version':'1'}
    b={'system':'urn:medikristal:test-procedure','code':'B','version':'1'}
    first = post(client, '/procedure-catalog', all_headers,
                 {'concept':a,'family':'panel','specimen_refs':[],'component_refs':[b],'detail_refs':[],'status':'active'}, 'proc-a')
    assert first.status_code == 201, first.text
    second = post(client, '/procedure-catalog', all_headers,
                  {'concept':b,'family':'panel','specimen_refs':[],'component_refs':[a],'detail_refs':[],'status':'active'}, 'proc-b')
    assert second.status_code == 409 and second.json()['code'] == 'catalog_reference_in_use'


def test_result_replacement_cannot_cross_case_boundary(client, all_headers):
    c1 = new_case(client, all_headers, 'result-c1')
    old = post(client, f"/cases/{c1['id']}/observations", all_headers, observation_body('cross-old'), 'cross-old', c1['revision']).json()
    c2 = new_case(client, all_headers, 'result-c2')
    item={'external_item_id':'replacement','replaces_id':old['id'],'observation':observation_body('replacement')}
    canonical={'owner':'synthetic-lab','report_id':'cross','report_version':'1','items':[item]}
    body={'case_revision':c2['revision'],**canonical,'digest':digest(canonical)}
    r=post(client,f"/cases/{c2['id']}/result-batches",all_headers,body,'cross-result',c2['revision'])
    assert r.status_code == 403 and r.json()['code'] == 'authorization_scope_mismatch'
    assert client.get(f"/api/v1/cases/{c2['id']}/observations",headers=all_headers).json()['items'] == []


def test_unconfigured_external_export_is_never_reported_as_success(client, all_headers):
    r=post(client,'/knowledge/exports',all_headers,
           {'release_ref':dict(syn.SYN_RELEASE),'target':'kristal_ses','policy_ref':dict(syn.AUTH_POLICY)},'export-unconfigured')
    assert r.status_code == 202, r.text
    assert r.json()['status'] == 'failed' and r.json()['error_code'] == 'capability_unavailable' and r.json()['result_ref'] is None


def test_plan_keeps_cost_perspectives_separate(client, all_headers):
    case = new_case(client, all_headers, 'plan-case')
    post(client, f"/cases/{case['id']}/observations", all_headers, observation_body('plan-obs'), 'plan-obs', case['revision'])
    case=client.get(f"/api/v1/cases/{case['id']}",headers=all_headers).json()
    _, ev = evaluate_binary(client, all_headers, case, 'plan-eval')
    proposals=client.get(f"/api/v1/cases/{case['id']}/proposals",headers=all_headers).json()['items']
    cap=_capability(client,all_headers,'plan')
    snap=_availability(client,all_headers,cap,key='plan-av')
    for key, perspective, amount in [('facility','facility',0),('patient','patient',500)]:
        q={'capability_id':cap['id'],'amount_minor':amount,'currency':'CAD','kind':'marginal','perspective':perspective,
           'valid_from':_future(-5),'valid_until':_future(60),'source':{'source_id':'synthetic','source_version':'1','record_id':key}}
        assert post(client,'/cost-quotes',all_headers,q,'plan-cost-'+key).status_code==201
    req={'case_id':case['id'],'case_revision':case['revision'],'evaluation_id':ev['id'],'proposal_ids':[p['id'] for p in proposals],
         'resource_snapshot_ids':[snap['id']],'policy_ref':dict(syn.POLICY)}
    op=post(client,'/plans',all_headers,req,'plan-compare')
    assert op.status_code==202,op.text
    plan=client.get('/api/v1/plans/'+op.json()['result_ref'],headers=all_headers).json()
    assert_schema('Plan',plan)
    test_comparison=next(c for c in plan['comparisons'] if c['strategy_ref']['id']==f"proposal:{next(p['id'] for p in proposals if p['kind']=='test')}")
    costs=[c for c in test_comparison['criteria'] if c['criterion_ref']['id'].startswith('cost:')]
    assert sorted(c['value'] for c in costs)==[0.0,500.0]
    assert len(costs)==2
