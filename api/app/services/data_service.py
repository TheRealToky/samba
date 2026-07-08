"""Query services for environmental datasets.

Implements the class diagram's SatelliteData.query() and ClimateData.query() as
service methods, returning GeoJSON-friendly dicts. Spatial filtering uses PostGIS
`ST_Intersects` against the GiST index (NFR-2).
"""
from __future__ import annotations

from datetime import datetime

from geoalchemy2.functions import ST_AsGeoJSON, ST_Intersects, ST_MakeEnvelope
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.environmental import ClimateData, SatelliteData


def _bbox_filter(column, bbox: tuple[float, float, float, float]):
    lon_min, lat_min, lon_max, lat_max = bbox
    return ST_Intersects(column, ST_MakeEnvelope(lon_min, lat_min, lon_max, lat_max, 4326))


class SatelliteService:
    def __init__(self, db: Session):
        self.db = db

    def query(
        self,
        region_id: int | None = None,
        bbox: tuple[float, float, float, float] | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 1000,
    ) -> list[dict]:
        stmt = select(
            SatelliteData.id, SatelliteData.ndvi, SatelliteData.date,
            SatelliteData.region_id, ST_AsGeoJSON(SatelliteData.location),
        )
        if region_id is not None:
            stmt = stmt.where(SatelliteData.region_id == region_id)
        if bbox is not None:
            stmt = stmt.where(_bbox_filter(SatelliteData.location, bbox))
        if start is not None:
            stmt = stmt.where(SatelliteData.date >= start)
        if end is not None:
            stmt = stmt.where(SatelliteData.date <= end)
        stmt = stmt.order_by(SatelliteData.date).limit(limit)
        return [
            {"id": i, "ndvi": float(n), "date": d, "region_id": rid, "location": geojson}
            for i, n, d, rid, geojson in self.db.execute(stmt).all()
        ]


class ClimateService:
    def __init__(self, db: Session):
        self.db = db

    def query(
        self,
        region_id: int | None = None,
        bbox: tuple[float, float, float, float] | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 1000,
    ) -> list[dict]:
        stmt = select(
            ClimateData.id, ClimateData.temperature, ClimateData.humidity,
            ClimateData.rainfall, ClimateData.date, ClimateData.region_id,
            ST_AsGeoJSON(ClimateData.location),
        )
        if region_id is not None:
            stmt = stmt.where(ClimateData.region_id == region_id)
        if bbox is not None:
            stmt = stmt.where(_bbox_filter(ClimateData.location, bbox))
        if start is not None:
            stmt = stmt.where(ClimateData.date >= start)
        if end is not None:
            stmt = stmt.where(ClimateData.date <= end)
        stmt = stmt.order_by(ClimateData.date).limit(limit)
        return [
            {
                "id": i, "temperature": t, "humidity": h, "rainfall": r,
                "date": d, "region_id": rid, "location": geojson,
            }
            for i, t, h, r, d, rid, geojson in self.db.execute(stmt).all()
        ]
