from __future__ import annotations

from medikristal.app import app
from medikristal.contracts import openapi_schema


def _contract_routes() -> set[tuple[str, str]]:
    routes: set[tuple[str, str]] = set()
    for path, item in openapi_schema()["paths"].items():
        for method in item:
            if method.lower() in {"get", "post", "put", "patch", "delete"}:
                routes.add((method.upper(), "/api/v1" + path))
    return routes


def _runtime_routes() -> set[tuple[str, str]]:
    routes: set[tuple[str, str]] = set()
    for route in app.routes:
        if not route.path.startswith("/api/v1"):
            continue
        for method in route.methods or set():
            if method in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
                routes.add((method, route.path))
    return routes


def test_runtime_route_set_matches_contract_exactly():
    assert _runtime_routes() == _contract_routes()
    assert len(_runtime_routes()) == 80


def test_served_openapi_is_checked_in_contract(client):
    assert client.get("/openapi.json").json() == openapi_schema()


def test_domain_errors_use_problem_json_and_correlation_id(client, all_headers):
    response = client.get("/api/v1/cases/00000000-0000-4000-8000-000000000404", headers=all_headers)
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.headers.get("x-correlation-id")
    body = response.json()
    assert body["status"] == 404 and body["code"] == "not_found"
    assert body["correlation_id"] == response.headers["x-correlation-id"]


def test_packaged_runtime_assets_match_repository_sources():
    from pathlib import Path
    from medikristal.config import PACKAGE_ROOT

    root = Path(__file__).resolve().parents[1]
    for name in ('domain.schema.json', 'openapi.json', 'traceability.json'):
        assert (PACKAGE_ROOT / '_assets' / 'contracts' / name).read_bytes() == (root / 'contracts' / name).read_bytes()
    for name in ('index.html', 'app.js', 'styles.css'):
        assert (PACKAGE_ROOT / '_assets' / 'frontend' / name).read_bytes() == (root / 'frontend' / name).read_bytes()
