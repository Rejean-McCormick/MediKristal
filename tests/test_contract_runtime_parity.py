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
