from __future__ import annotations

from .conftest import signed_token
from .helpers import new_case, post


def test_at015_cross_tenant_uuid_does_not_leak(client, tenant_one, tenant_two):
    t1={"Authorization":"Bearer "+signed_token(tenant_one,"p1",["cases:*"])}
    t2={"Authorization":"Bearer "+signed_token(tenant_two,"p2",["cases:read"])}
    case=new_case(client,t1)
    r=client.get(f"/api/v1/cases/{case['id']}",headers=t2)
    assert r.status_code==404
    assert r.json()['detail']=="Ressource introuvable."


def test_at023_paid_mode_does_not_grant_order_permission(client, tenant_one):
    admin={"Authorization":"Bearer "+signed_token(tenant_one,"admin",["configuration:*","cases:*","knowledge:read"])}
    patient={"Authorization":"Bearer "+signed_token(tenant_one,"patient",["cases:read","cases:create","observations:write"])}
    cfg=client.get('/api/v1/configuration',headers=admin)
    assert cfg.status_code==200
    body={"mode":"online_extended","network_scope":"internet","intended_use":"engineering","execution_policy":"protocol_authorized","provider_allowlist":[],"paid_budget_minor":100,"currency":"CAD","local_release_ref":None}
    r=post(client,'/configuration/changes',admin,body,'cfg',int(cfg.headers['ETag'].strip('"')))
    assert r.status_code==200
    # Permission is still absent even in the extended paid profile.
    r=client.post('/api/v1/orders',headers={**patient,'Idempotency-Key':'x'},json={"proposal_id":"00000000-0000-4000-8000-000000000001","case_revision":1,"destination":"synthetic","authorization_policy_ref":{"id":"engineering-only","version":"0.1.0","digest":"sha256:"+'a'*64}})
    assert r.status_code==403 and r.json()['code']=='permission_denied'


def test_missing_if_match_is_428(client, all_headers):
    case=new_case(client,all_headers)
    r=client.post(f"/api/v1/cases/{case['id']}/transitions",headers={**all_headers,"Idempotency-Key":"no-match"},json={"target":"waiting","reason":"test"})
    assert r.status_code==428


def test_token_cli_emits_case_grants(monkeypatch, capsys, tenant_one):
    from medikristal.security import decode_token
    from medikristal.token_cli import main
    case_id = '00000000-0000-4000-8000-000000000123'
    monkeypatch.setattr('sys.argv', [
        'medikristal-token', '--tenant', tenant_one, '--principal', 'professional-cli',
        '--permission', 'cases:read', '--case-grant', case_id, '--ttl', '3600',
    ])
    main()
    token = capsys.readouterr().out.strip()
    ctx = decode_token(token)
    assert ctx.tenant_id == tenant_one
    assert ctx.principal_id == 'professional-cli'
    assert ctx.permissions == frozenset({'cases:read'})
    assert ctx.case_grants == frozenset({case_id})


def test_case_operation_does_not_leak_to_principal_without_case_grant(client, all_headers, tenant_one):
    from medikristal import synthetic as syn
    from .helpers import evaluate_binary, new_case, observation_body, post
    from .conftest import signed_token

    case = new_case(client, all_headers, 'operation-scope-case')
    assert post(client, f"/cases/{case['id']}/observations", all_headers, observation_body('operation-scope-obs'), 'operation-scope-obs', case['revision']).status_code == 200
    case = client.get(f"/api/v1/cases/{case['id']}", headers=all_headers).json()
    operation, _ = evaluate_binary(client, all_headers, case, 'operation-scope-eval')

    outsider = {'Authorization': 'Bearer ' + signed_token(tenant_one, 'ops-outsider', ['operations:read'])}
    hidden = client.get(f"/api/v1/operations/{operation['id']}", headers=outsider)
    assert hidden.status_code == 404 and hidden.json()['code'] == 'not_found'

    granted = {'Authorization': 'Bearer ' + signed_token(tenant_one, 'ops-insider', ['operations:read'], [case['id']])}
    visible = client.get(f"/api/v1/operations/{operation['id']}", headers=granted)
    assert visible.status_code == 200 and visible.json()['id'] == operation['id']
