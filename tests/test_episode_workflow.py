from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from tests.conftest import signed_token


PREFIX = "/api/v2"
VALUES = {"values": {"discomfort": "present", "itch": "absent", "alarm": "absent"}}


def command(client, headers, path, body, revision=None, key=None, method="POST"):
    headers = {**headers, "Idempotency-Key": key or str(uuid4())}
    if revision is not None:
        headers["If-Match"] = f'"{revision}"'
    return client.request(method, PREFIX + path, json=body, headers=headers)


def opened(client, headers, name="Épisode fictif"):
    response = command(client, headers, "/episodes", {"title": name})
    assert response.status_code == 201, response.text
    return response.json()


def collected(client, headers):
    item = opened(client, headers)
    response = command(client, headers, f"/episodes/{item['id']}/observations", VALUES, item["revision"])
    assert response.status_code == 200, response.text
    return response.json()


def test_complete_automatic_lab_loop_and_correction(client, all_headers):
    data = collected(client, all_headers)
    url = f"/episodes/{data['id']}"
    assert [(choice["test"], choice["expected_cost_minor"]) for choice in data["choices"]] == [
        ("screen", 6900), ("direct", 18000),
    ]
    assert data["assessment"]["estimate"]["value_percent"] == 20
    response = command(client, all_headers, url + "/orders", {"test": "screen"}, data["revision"])
    assert response.status_code == 200, response.text
    order = response.json()
    result_url = url + f"/orders/{order['order']['id']}/result"
    response = command(client, all_headers, result_url, {"value": "negative", "version": 1}, order["revision"])
    assert response.status_code == 200, response.text
    reported = response.json()
    assert reported["assessment"]["review_kind"] == "excluded"
    assert reported["order"] is None
    signed = command(client, all_headers, url + "/decision", {"disposition": "accept"}, reported["revision"]).json()
    assert signed["status"] == "closed"
    assert signed["decision"]["signed_revision"] == reported["revision"]
    replay = command(client, all_headers, result_url, {"value": "negative", "version": 1}, order["revision"])
    assert replay.status_code == 200 and replay.json()["revision"] == signed["revision"]
    collision = command(client, all_headers, result_url, {"value": "positive", "version": 1}, signed["revision"])
    assert collision.status_code == 409
    corrected = command(client, all_headers, result_url, {"value": "positive", "version": 2}, signed["revision"]).json()
    assert corrected["decision_needs_review"] and corrected["status"] == "open"
    assert corrected["assessment"]["phase"] == "investigate"
    assert corrected["choices"][0]["test"] == "direct"
    historical_replay = command(client, all_headers, result_url, {"value": "negative", "version": 1}, order["revision"])
    assert historical_replay.json()["revision"] == corrected["revision"]


def test_grants_urgency_and_role_separation(client, tenant_one, tenant_two):
    def role(name, perms, tenant=tenant_one):
        return {"Authorization": "Bearer " + signed_token(tenant, name, [f"episode:{p}" for p in perms])}
    patient = role("patient-fictif", ["read", "collect", "share"])
    reviewer = role("equipe-fictive", ["read", "sign"])
    stranger = role("autre-tenant", ["read"], tenant_two)
    data = opened(client, patient)
    url = f"/episodes/{data['id']}"
    assert client.get(PREFIX + url, headers=reviewer).status_code == 404
    assert client.get(PREFIX + url, headers=stranger).status_code == 404
    data = command(client, patient, url + "/grants", {"principal": "equipe-fictive"}, data["revision"]).json()
    data = command(client, patient, url + "/observations", {"values": {"alarm": "present"}}, data["revision"]).json()
    assert data["assessment"]["phase"] == "urgent"
    assert data["choices"] == []
    assert client.get(PREFIX + url, headers=reviewer).status_code == 200
    assert command(client, patient, url + "/decision", {"disposition": "accept"}, data["revision"]).status_code == 403
    response = command(client, reviewer, url + "/decision", {"disposition": "escalate", "note": "Signal de simulation"},
                       data["revision"])
    assert response.status_code == 200 and response.json()["status"] == "closed"


def test_capacity_change_and_competing_orders(client, all_headers):
    first = collected(client, all_headers)
    second = collected(client, all_headers)
    before = client.get(PREFIX + "/resources", headers=all_headers).json()
    edit = command(client, all_headers, "/resources/screen",
                   {"minutes": 75, "capacity": 0, "cost_minor": None},
                   before["screen"]["revision"], method="PUT")
    assert edit.status_code == 200, edit.text
    reload = client.get(PREFIX + f"/episodes/{first['id']}", headers=all_headers).json()
    assert reload["assessment"] == first["assessment"]
    assert reload["choices"][0]["test"] == "direct" and reload["choices"][0]["available"]
    assert not reload["choices"][1]["available"] and reload["choices"][1]["expected_cost_minor"] is None

    def request_order(episode):
        return command(client, all_headers, f"/episodes/{episode['id']}/orders", {"test": "direct"}, episode["revision"])

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(request_order, [first, second]))
    assert sorted(result.status_code for result in results) == [200, 409]
    won, = [r.json() for r in results if r.status_code == 200]
    path = f"/episodes/{won['id']}/orders/{won['order']['id']}"
    cancelled = command(client, all_headers, path + "/cancel", {"reason": "Essai de reprise"}, won["revision"])
    assert cancelled.status_code == 200
    assert client.get(PREFIX + "/resources", headers=all_headers).json()["direct"]["available"] == 1


def test_consented_analytics_and_independent_verification(client, all_headers, tenant_one):
    episode = collected(client, all_headers)
    url = f"/episodes/{episode['id']}"
    verifier = {"Authorization": "Bearer " + signed_token(tenant_one, "relecteur",
                                                            ["episode:verify"], [episode["id"]])}
    data = command(client, all_headers, url + "/orders", {"test": "direct"}, episode["revision"]).json()
    data = command(client, all_headers, url + f"/orders/{data['order']['id']}/result",
                   {"value": "positive", "version": 1}, data["revision"]).json()
    data = command(client, all_headers, url + "/decision", {"disposition": "accept"}, data["revision"]).json()
    outcome = {"value": "confirmed", "evidence": "Vérification synthétique indépendante"}
    assert command(client, all_headers, url + "/verified-outcome", outcome, data["revision"]).status_code == 403
    data = command(client, verifier, url + "/verified-outcome", outcome, data["revision"]).json()
    assert client.get(PREFIX + "/statistics", headers=all_headers).json()["scenario_counts"] == {}
    data = command(client, all_headers, url + "/statistics-consent", {"include": True}, data["revision"]).json()
    stats = client.get(PREFIX + "/statistics", headers=all_headers).json()
    assert stats["scenario_counts"] == {"confirmed": 1}
    assert stats["verified_evaluation"]["count"] == 1
    assert round(stats["verified_evaluation"]["brier"], 2) == 0.64
    assert command(client, all_headers, url + "/statistics-consent", {"include": False}, data["revision"]).status_code == 200
    assert client.get(PREFIX + "/statistics", headers=all_headers).json()["verified_evaluation"]["count"] == 0


def test_versioned_api_and_local_lookup(client, all_headers, monkeypatch, tmp_path):
    import sqlite3
    from scripts.import_medical_sources import SCHEMA
    index = tmp_path / "public.sqlite3"
    with sqlite3.connect(index) as db:
        db.executescript(SCHEMA)
        db.execute("INSERT INTO source_file VALUES (1, 'fixture', 'file.zip', 'digest', '{}')")
        db.execute("INSERT INTO record VALUES (1, 1, 'product', 'ABC-12', 'Libellé public', '{}')")
        db.execute("INSERT INTO lookup(rowid, label) VALUES (1, 'Libellé public')")
    monkeypatch.setenv("MEDIKRISTAL_PUBLIC_INDEX", str(index))
    episode = opened(client, all_headers)
    projection = client.get(PREFIX + f"/episodes/{episode['id']}/projection", headers=all_headers)
    assert projection.json()["recipe_candidate"] == "dossier-medical"
    assert projection.json()["reference"]["package"] == episode["package_ref"]
    assert projection.json()["digest"].startswith("sha256:")
    assert "/api/v2/episodes/{episode_id}" in client.get(PREFIX + "/openapi.json").json()["paths"]
    for text in ("ABC-12", "libelle"):
        response = client.get(PREFIX + "/references", params={"q": text}, headers=all_headers)
        assert response.status_code == 200, response.text
        assert response.json()["items"][0]["code"] == "ABC-12"


def test_local_workshop_rejects_untrusted_origin_and_unrelated_host(client, monkeypatch):
    from dataclasses import replace

    from medikristal import episodes as module

    monkeypatch.setattr(module, "settings", replace(module.settings, local_episode_demo=True))
    assert client.get(PREFIX + "/catalog", headers={"Host": "127.0.0.1:8001"}).status_code == 200
    assert client.get(PREFIX + "/catalog", headers={"Host": "atelier.exemple"}).status_code == 401
    assert client.get(PREFIX + "/catalog", headers={
        "Host": "127.0.0.1:8001", "Origin": "https://origine.exemple",
    }).status_code == 401
