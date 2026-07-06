"""Tests for the rule-based detector and the POST /analyze endpoint."""
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models
from app.database import Base, get_db
from app.detection import NDVIPoint, detect_region_events, severity_for_loss
from app.main import app
from app.security import create_access_token, hash_password

START = date(2026, 1, 1)


def _weekly(values):
    """Build weekly NDVIPoints from a list of ndvi values."""
    return [NDVIPoint(date=START + timedelta(weeks=i), ndvi=v) for i, v in enumerate(values)]


# --------------------------- pure detector ---------------------------

def test_flags_synthetic_ndvi_drop():
    # Healthy 0.80 for 12 weeks, then clears to 0.40.
    series = _weekly([0.80] * 12 + [0.40] * 12)
    events = detect_region_events("Menabe Corridor", series, drop_threshold_pct=25, window_days=60)

    assert len(events) == 1
    ev = events[0]
    assert ev.polygon_location == "Menabe Corridor"
    assert ev.vegetation_loss == pytest.approx(50.0, abs=0.1)  # (0.80-0.40)/0.80
    assert ev.start_date < ev.end_date
    assert severity_for_loss(ev.vegetation_loss) == "high"


def test_stable_series_produces_no_event():
    series = _weekly([0.80] * 24)
    events = detect_region_events("Ankarafa Reserve", series, drop_threshold_pct=25, window_days=60)
    assert events == []


def test_drop_below_threshold_is_ignored():
    # 15% drop (0.80 -> 0.68) is under the 25% threshold.
    series = _weekly([0.80] * 12 + [0.68] * 12)
    events = detect_region_events("Tsingy Verde", series, drop_threshold_pct=25, window_days=60)
    assert events == []


def test_severity_bands():
    assert severity_for_loss(30) == "moderate"
    assert severity_for_loss(50) == "high"
    assert severity_for_loss(70) == "critical"


# --------------------------- /analyze endpoint ---------------------------

@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    # Seed a user + a region with a clear NDVI drop.
    db = TestingSession()
    user = models.User(
        name="Test", email="t@samba.mg", password_hash=hash_password("pw"), role="researcher"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    for i, v in enumerate([0.80] * 12 + [0.40] * 12):
        db.add(models.SatelliteData(
            polygon_location="Menabe Corridor", ndvi=v, date=START + timedelta(weeks=i)
        ))
    db.commit()
    token = create_access_token(user.id)
    db.close()

    c = TestClient(app)
    c.headers.update({"Authorization": f"Bearer {token}"})
    yield c
    app.dependency_overrides.clear()


def test_analyze_creates_event_and_alert(client):
    resp = client.post("/analyze")
    assert resp.status_code == 200
    body = resp.json()
    assert body["regions_scanned"] == 1
    assert body["events_created"] == 1
    assert body["alerts_created"] == 1

    alerts = client.get("/alerts").json()
    assert len(alerts) == 1
    assert alerts[0]["severity"] == "high"
    assert "Menabe Corridor" in alerts[0]["message"]


def test_analyze_requires_auth():
    # No override needed; a bare client has no token.
    resp = TestClient(app).post("/analyze")
    assert resp.status_code == 401
