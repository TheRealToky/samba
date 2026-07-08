"""Unit tests for the cleaning/normalization stage (no DB)."""
from __future__ import annotations

from datetime import datetime, timezone

from app.ingestion.base import ClimateRecord, ObservationRecord, SatelliteRecord
from app.processing.cleaning import clean_climate, clean_observations, clean_satellite

_WKT = "POLYGON((46 -19, 47 -19, 47 -18, 46 -18, 46 -19))"
_D = datetime(2023, 1, 1, tzinfo=timezone.utc)


def test_clean_satellite_drops_out_of_range_and_dupes():
    recs = [
        SatelliteRecord(date=_D, ndvi=0.7, location_wkt=_WKT),
        SatelliteRecord(date=_D, ndvi=0.7, location_wkt=_WKT),   # duplicate
        SatelliteRecord(date=_D, ndvi=5.0, location_wkt=_WKT),   # out of [-1,1]
    ]
    out = clean_satellite(recs)
    assert len(out) == 1
    assert out[0].ndvi == 0.7


def test_clean_climate_nulls_impossible_values():
    rec = ClimateRecord(date=_D, temperature=200.0, humidity=250.0, rainfall=-5.0, location_wkt=_WKT)
    out = clean_climate([rec])
    # all three invalid -> record dropped entirely
    assert out == []

    rec2 = ClimateRecord(date=_D, temperature=25.0, humidity=250.0, rainfall=-5.0, location_wkt=_WKT)
    out2 = clean_climate([rec2])
    assert len(out2) == 1
    assert out2[0].temperature == 25.0
    assert out2[0].humidity is None and out2[0].rainfall is None


def test_clean_observations_trims_to_madagascar():
    inside = ObservationRecord(date=_D, scientific_name="Indri indri", lon=47.0, lat=-18.9, source="gbif")
    outside = ObservationRecord(date=_D, scientific_name="X", lon=2.3, lat=48.8, source="gbif")  # Paris
    out = clean_observations([inside, outside])
    assert len(out) == 1
    assert out[0].scientific_name == "Indri indri"
