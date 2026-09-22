from __future__ import annotations

from medikristal import synthetic as syn
from .helpers import evaluate_binary, new_case, observation_body, post


def test_at011_unknown_allergy_needs_information_and_care_plan_is_not_order(client, all_headers):
    case=new_case(client,all_headers)
    post(client,f"/cases/{case['id']}/observations",all_headers,observation_body(),"obs",case['revision'])
    case=client.get(f"/api/v1/cases/{case['id']}",headers=all_headers).json()
    _,ev=evaluate_binary(client,all_headers,case)
    body={"case_revision":case['revision'],"evaluation_id":ev['id'],"protocol_refs":[dict(syn.PROTOCOL)]}
    o=post(client,f"/cases/{case['id']}/treatment-evaluations",all_headers,body,'tx',case['revision'])
    assert o.status_code==202
    option=client.get(f"/api/v1/cases/{case['id']}/treatment-options",headers=all_headers).json()['items'][0]
    assert option['status']=='needs_information'
    plan_body={"case_revision":case['revision'],"treatment_option_ids":[option['id']],"followup_task_ids":[],"reason":"plan synthétique"}
    cp=post(client,f"/cases/{case['id']}/care-plans",all_headers,plan_body,'care',case['revision'])
    assert cp.status_code==200
    assert cp.json()['status']=='active'
    # No ServiceOrder is created by a care plan.
    from medikristal.db import SessionLocal, Entity
    from sqlalchemy import select, func
    with SessionLocal() as db:
        count=db.scalar(select(func.count()).select_from(Entity).where(Entity.kind=='ServiceOrder'))
    assert count==0


def test_at012_accepted_contribution_does_not_activate_release(client, all_headers):
    scope={"population_id":"synthetic-only","setting":"engineering","jurisdiction":"TEST","language":"fr","valid_from":"2026-09-22T12:00:00Z","valid_until":None}
    body={"kind":"model","target_ref":{"id":"synthetic-binary","version":"0.1.0","digest":"sha256:"+'a'*64},"proposed_artifact_ref":{"id":"candidate","version":"0.2.0","digest":"sha256:"+'b'*64},"rationale":"correction fictive","evidence_refs":[],"scope":scope}
    c=post(client,'/contributions',all_headers,body,'contrib')
    assert c.status_code==201
    review={"verdict":"accept","rationale":"fixture","evidence_refs":[],"conflict_of_interest":"none"}
    accepted=post(client,f"/contributions/{c.json()['id']}/reviews",all_headers,review,'review',c.json()['revision'])
    assert accepted.status_code==200 and accepted.json()['status']=='accepted'
    cfg=client.get('/api/v1/configuration',headers=all_headers).json()
    assert cfg['local_release_ref'] is None


def test_at027_workflow_rechecks_case_revision(client, all_headers):
    case=new_case(client,all_headers)
    proto=client.get('/api/v1/knowledge/protocols',headers=all_headers).json()['items'][0]
    body={"case_id":case['id'],"case_revision":case['revision'],"protocol_ref":{"id":proto['id'],"version":proto['version'],"digest":proto['digest']},"authorization_policy_ref":dict(syn.AUTH_POLICY),"intended_use":"engineering"}
    wf=post(client,'/workflows',all_headers,body,'wf').json()
    # Change the case before the workflow command.
    case2=post(client,f"/cases/{case['id']}/transitions",all_headers,{"target":"waiting","reason":"new input"},'case-change',case['revision']).json()
    r=post(client,f"/workflows/{wf['id']}/transitions",all_headers,{"action":"start","reason":"go","case_revision":case['revision']},'wf-start',wf['revision'])
    assert r.status_code==409 and r.json()['code']=='stale_case'
