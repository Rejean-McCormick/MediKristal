from __future__ import annotations

from medikristal import synthetic as syn

from .helpers import assert_schema, evaluate_binary, new_case, observation_body, post


def test_at001_offline_vertical_slice(client, all_headers):
    caps = client.get("/api/v1/capabilities", headers=all_headers).json()
    assert caps["mode"] == "offline_free"
    assert caps["network_scope"] == "none"
    case = new_case(client, all_headers)
    r = post(client, f"/cases/{case['id']}/observations", all_headers, observation_body(), "obs-1", case["revision"])
    assert r.status_code == 200
    case = client.get(f"/api/v1/cases/{case['id']}", headers=all_headers).json()
    _, evaluation = evaluate_binary(client, all_headers, case)
    assert evaluation["status"] == "complete"
    assert abs(evaluation["hypotheses"][0]["probability"] - 0.47058823529411764) < 1e-12
    proposals = client.get(f"/api/v1/cases/{case['id']}/proposals", headers=all_headers).json()["items"]
    assert {p["kind"] for p in proposals} == {"ask", "observe", "test"}
    assert_schema("ClinicalCase", case)
    assert_schema("Evaluation", evaluation)
    for p in proposals: assert_schema("ActionProposal", p)


def test_idempotency_same_request_returns_same_resource_and_conflict_on_change(client, all_headers):
    body={"subject_ref":"00000000-0000-4000-8000-000000000003","intended_use":"engineering","language":"fr","synthetic":True,"context_refs":[]}
    a=post(client,"/cases",all_headers,body,"same-key")
    b=post(client,"/cases",all_headers,body,"same-key")
    assert a.status_code == b.status_code == 201
    assert a.json()["id"] == b.json()["id"]
    changed={**body,"language":"en"}
    c=post(client,"/cases",all_headers,changed,"same-key")
    assert c.status_code == 409
    assert c.json()["code"] == "idempotency_conflict"


def test_at004_source_version_duplicate_and_conflict(client, all_headers):
    case = new_case(client, all_headers)
    body=observation_body("external-one")
    a=post(client,f"/cases/{case['id']}/observations",all_headers,body,"o1",case["revision"])
    assert a.status_code==200
    case2=client.get(f"/api/v1/cases/{case['id']}",headers=all_headers).json()
    b=post(client,f"/cases/{case['id']}/observations",all_headers,body,"o2",case2["revision"])
    assert b.status_code==200 and b.json()["id"]==a.json()["id"]
    case3=client.get(f"/api/v1/cases/{case['id']}",headers=all_headers).json()
    divergent=observation_body("external-one", value=False)
    c=post(client,f"/cases/{case['id']}/observations",all_headers,divergent,"o3",case3["revision"])
    assert c.status_code==409 and c.json()["code"]=="source_version_conflict"


def test_at006_score_is_not_probability(client, all_headers):
    case=new_case(client,all_headers)
    models=client.get('/api/v1/knowledge/models',headers=all_headers).json()['items']
    score=next(m for m in models if m['id']=='synthetic-score')
    body={"case_revision":case['revision'],"knowledge_release":dict(syn.SYN_RELEASE),"model_refs":[{"id":score['id'],"version":score['version'],"digest":score['digest']}],"evaluation_time":"2026-09-22T12:00:00Z","intended_use":"engineering"}
    r=post(client,f"/cases/{case['id']}/evaluations",all_headers,body,"score-eval",case['revision'])
    assert r.status_code==202
    ev=client.get('/api/v1/evaluations/'+r.json()['result_ref'],headers=all_headers).json()
    h=ev['hypotheses'][0]
    assert h['kind']=='score' and h['score']==0.73 and h['probability'] is None
    assert 'not_estimable' in h['reason_codes']
    assert_schema('Evaluation',ev)


def test_at007_amendment_keeps_history_and_stales_evaluation(client, all_headers):
    case=new_case(client,all_headers)
    obs=post(client,f"/cases/{case['id']}/observations",all_headers,observation_body(),"obs",case['revision']).json()
    case=client.get(f"/api/v1/cases/{case['id']}",headers=all_headers).json()
    _,ev=evaluate_binary(client,all_headers,case)
    amendment={"reason":"correction synthétique","replacement":observation_body("obs-corrected",value=False)}
    r=post(client,f"/observations/{obs['id']}/amendments",all_headers,amendment,"amend",obs['revision'])
    assert r.status_code==200
    old=client.get(f"/api/v1/cases/{case['id']}/observations",headers=all_headers).json()['items']
    assert len(old)==2
    assert next(x for x in old if x['id']==obs['id'])['status']=='amended'
    stale=client.get(f"/api/v1/evaluations/{ev['id']}",headers=all_headers).json()
    assert stale['stale'] is True
    proposals=client.get(f"/api/v1/cases/{case['id']}/proposals",headers=all_headers).json()['items']
    assert all(p['status']=='superseded' for p in proposals)
