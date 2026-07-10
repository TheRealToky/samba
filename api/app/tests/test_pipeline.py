"""Integration test: sample ingestion -> query -> alignment (DB-backed)."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from geoalchemy2.elements import WKTElement
from sqlalchemy import select

from app.db import SessionLocal
from app.geo.madagascar import REGIONS, bbox_polygon_wkt
from app.ingestion.service import IngestionService
from app.models.region import Region
from app.processing.alignment import align_region, ndvi_series


@pytest.fixture
def region_id() -> int:
    """Use a seeded region, or create MENABE if the test DB has no seed."""
    with SessionLocal() as db:
        region = db.execute(select(Region).where(Region.code == "MENABE")).scalar_one_or_none()
        if region is None:
            spec = next(r for r in REGIONS if r["code"] == "MENABE")
            region = Region(
                code=spec["code"], name=spec["name"], biome=spec["biome"],
                geom=WKTElement(bbox_polygon_wkt(tuple(spec["bbox"])), srid=4326),
            )
            db.add(region)
            db.commit()
            db.refresh(region)
        return region.id


def test_sample_ingestion_and_alignment(region_id: int):
    start = datetime(2023, 1, 1, tzinfo=timezone.utc)
    end = datetime(2023, 6, 30, tzinfo=timezone.utc)
    with SessionLocal() as db:
        region = db.get(Region, region_id)
        svc = IngestionService(db)
        n_sat = svc.ingest_satellite(region, start, end)
        n_clim = svc.ingest_climate(region, start, end)
        n_obs = svc.ingest_observations(region, start, end, limit=20)

        assert n_sat > 0 and n_clim > 0 and n_obs > 0

        series = ndvi_series(db, region_id)
        assert len(series) >= n_sat
        # NDVI values are physically plausible
        assert all(-1.0 <= v <= 1.0 for _, v in series)

        aligned = align_region(db, region_id, start=start, end=end)
        assert len(aligned) > 0
        assert any(r.ndvi is not None for r in aligned)
