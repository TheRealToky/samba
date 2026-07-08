"""Cleaning + normalization (FR-2.1): drop impossible values, de-duplicate.

Garbage-in-garbage-out guard for the ML stage. Kept as pure functions over the
ingestion dataclasses so they're unit-testable without a database.
"""
from __future__ import annotations

from app.ingestion.base import ClimateRecord, ObservationRecord, SatelliteRecord


def clean_satellite(records: list[SatelliteRecord]) -> list[SatelliteRecord]:
    seen: set = set()
    out: list[SatelliteRecord] = []
    for r in records:
        if r.ndvi is None or not (-1.0 <= r.ndvi <= 1.0):
            continue
        key = (r.location_wkt, r.date.date())
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def clean_climate(records: list[ClimateRecord]) -> list[ClimateRecord]:
    out: list[ClimateRecord] = []
    for r in records:
        temp = r.temperature if r.temperature is not None and -90 <= r.temperature <= 60 else None
        rain = r.rainfall if r.rainfall is not None and r.rainfall >= 0 else None
        hum = r.humidity if r.humidity is not None and 0 <= r.humidity <= 100 else None
        if temp is None and rain is None and hum is None:
            continue
        out.append(ClimateRecord(date=r.date, temperature=temp, humidity=hum, rainfall=rain, location_wkt=r.location_wkt))
    return out


def clean_observations(records: list[ObservationRecord]) -> list[ObservationRecord]:
    out: list[ObservationRecord] = []
    for r in records:
        if not r.scientific_name:
            continue
        if not (-90 <= r.lat <= 90 and -180 <= r.lon <= 180):
            continue
        # Trim to Madagascar's rough envelope to drop obviously-wrong points.
        if not (43.0 <= r.lon <= 51.0 and -26.0 <= r.lat <= -11.5):
            continue
        r.scientific_name = r.scientific_name.strip()
        out.append(r)
    return out
