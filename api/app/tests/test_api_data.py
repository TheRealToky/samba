"""API-level checks for the Phase 2/4 read surface."""
from __future__ import annotations

from fastapi.testclient import TestClient


def test_regions_public(client: TestClient):
    resp = client.get("/api/v1/regions")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_regions_geojson_shape(client: TestClient):
    resp = client.get("/api/v1/regions/geojson")
    assert resp.status_code == 200
    body = resp.json()
    assert body["type"] == "FeatureCollection"
    assert isinstance(body["features"], list)


def test_ingestion_summary(client: TestClient):
    resp = client.get("/api/v1/ingestion/summary")
    assert resp.status_code == 200
    body = resp.json()
    for key in ("regions", "satellite_data", "climate_data", "species", "species_observations"):
        assert key in body


def test_ingestion_requires_role(client: TestClient):
    # unauthenticated ingestion trigger is rejected
    resp = client.post("/api/v1/ingestion/run", json={"start": "2023-01-01", "end": "2023-02-01"})
    assert resp.status_code == 401


def test_alerts_require_auth(client: TestClient):
    assert client.get("/api/v1/alerts").status_code == 401
