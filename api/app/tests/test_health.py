from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_liveness(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_health_db_and_postgis(client: TestClient) -> None:
    resp = client.get("/health/db")
    assert resp.status_code == 200
    body = resp.json()
    assert body["database"] == "reachable"
    assert body["postgis"]  # PostGIS version string present
