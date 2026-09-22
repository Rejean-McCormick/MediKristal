from __future__ import annotations

from .conftest import signed_token
from .helpers import evaluate_binary, new_case, observation_body, post


def test_at005_broader_mapping_never_satisfies_exact_equivalence_query(client, all_headers):
    broader = client.get('/api/v1/knowledge/assertions', headers=all_headers, params={
        'subject_code': 'SYN-T1-BROAD', 'predicate': 'broader_than', 'object_code': 'SYN-T1',
    })
    assert broader.status_code == 200, broader.text
    assert [item['predicate'] for item in broader.json()['items']] == ['broader_than']

    exact = client.get('/api/v1/knowledge/assertions', headers=all_headers, params={
        'subject_code': 'SYN-T1-BROAD', 'predicate': 'equivalent_to', 'object_code': 'SYN-T1',
    })
    assert exact.status_code == 200, exact.text
    assert exact.json()['items'] == []


def test_at019_capability_registry_does_not_claim_clinical_qualification(client, all_headers):
    response = client.get('/api/v1/capabilities', headers=all_headers)
    assert response.status_code == 200, response.text
    for capability in response.json()['capabilities']:
        assert capability['supported_uses'] == ['engineering']
        assert capability['limitations']
    states = {item['name']: item['state'] for item in response.json()['capabilities']}
    assert states['fhir_partner'] == 'not_configured'
    assert states['kristal_export'] == 'not_configured'


def test_at025_api_only_clients_keep_knowledge_and_case_permissions_separate(client, all_headers, tenant_one):
    case = new_case(client, all_headers, 'at025-case')
    recorded = post(client, f"/cases/{case['id']}/observations", all_headers, observation_body('at025-obs'), 'at025-obs', case['revision'])
    assert recorded.status_code == 200
    case = client.get(f"/api/v1/cases/{case['id']}", headers=all_headers).json()
    _, evaluation = evaluate_binary(client, all_headers, case, 'at025-eval')

    knowledge_only = {'Authorization': 'Bearer ' + signed_token(tenant_one, 'api-knowledge', ['knowledge:read'])}
    assertion = client.get('/api/v1/knowledge/assertions', headers=knowledge_only)
    assert assertion.status_code == 200 and assertion.json()['items']
    denied_eval = client.get(f"/api/v1/evaluations/{evaluation['id']}", headers=knowledge_only)
    assert denied_eval.status_code == 403

    case_reader = {'Authorization': 'Bearer ' + signed_token(tenant_one, 'api-case-reader', ['cases:read'], [case['id']])}
    allowed_eval = client.get(f"/api/v1/evaluations/{evaluation['id']}", headers=case_reader)
    assert allowed_eval.status_code == 200
    denied_knowledge = client.get('/api/v1/knowledge/assertions', headers=case_reader)
    assert denied_knowledge.status_code == 403
