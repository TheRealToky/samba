"""Unit tests for the ML baselines (no DB)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.ingestion.sampling import sample_satellite
from app.ml.changepoint import detect_change_point


def _series(values):
    start = datetime(2022, 1, 1, tzinfo=timezone.utc)
    return [(start + timedelta(days=7 * i), v) for i, v in enumerate(values)]


def test_changepoint_detects_clear_drop():
    series = _series([0.8] * 30 + [0.5] * 30)
    cp = detect_change_point(series)
    assert cp is not None
    assert 0.25 <= cp.drop <= 0.35
    assert cp.relative_loss > 0.2
    assert cp.p_value <= 0.05


def test_changepoint_ignores_stable_series():
    series = _series([0.8, 0.81, 0.79, 0.8] * 15)
    assert detect_change_point(series) is None


def test_sampling_is_deterministic_and_declining_region_drops():
    region = {"code": "MENABE", "name": "Menabe", "bbox": (43.9, -20.6, 45.4, -19.2), "biome": "dry_deciduous"}
    start = datetime(2022, 1, 1, tzinfo=timezone.utc)
    end = datetime(2024, 12, 31, tzinfo=timezone.utc)
    a = sample_satellite(region, start, end)
    b = sample_satellite(region, start, end)
    assert [r.ndvi for r in a] == [r.ndvi for r in b]  # deterministic
    # declining region: end materially below start
    assert a[0].ndvi - a[-1].ndvi > 0.1
