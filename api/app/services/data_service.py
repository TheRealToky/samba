"""Query services for environmental datasets.

Implements the class diagram's SatelliteData.query() and ClimateData.query() as
service methods, returning GeoJSON-friendly dicts. Spatial filtering uses PostGIS
`ST_Intersects` against the GiST index (NFR-2).
"""
from __future__ import annotations

from datetime import datetime

from geoalchemy2.functions import ST_AsGeoJSON, ST_Intersects, ST_MakeEnvelope
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.environmental import ClimateData, SatelliteData
from app.models.region import Region


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


class ClimateAnalyticsService:
    """Aggregations that power the national Climate dashboard.

    Combines ClimateData (temperature / rainfall / humidity) with SatelliteData
    (NDVI) so climate and vegetation trends can be read on one timeline."""

    def __init__(self, db: Session):
        self.db = db

    def national_monthly(self) -> list[dict]:
        """Country-wide monthly averages across every region."""
        cm = func.date_trunc("month", ClimateData.date)
        climate_rows = self.db.execute(
            select(
                cm.label("m"),
                func.avg(ClimateData.temperature),
                func.avg(ClimateData.rainfall),
                func.avg(ClimateData.humidity),
            ).group_by("m").order_by("m")
        ).all()

        sm = func.date_trunc("month", SatelliteData.date)
        ndvi_rows = self.db.execute(
            select(sm.label("m"), func.avg(SatelliteData.ndvi)).group_by("m").order_by("m")
        ).all()
        ndvi_by_month = {m.date().isoformat(): float(v) for m, v in ndvi_rows if v is not None}

        out: list[dict] = []
        for m, temp, rain, hum in climate_rows:
            key = m.date().isoformat()
            out.append(
                {
                    "month": key,
                    "temperature": round(float(temp), 2) if temp is not None else None,
                    "rainfall": round(float(rain), 1) if rain is not None else None,
                    "humidity": round(float(hum), 1) if hum is not None else None,
                    "ndvi": round(ndvi_by_month[key], 4) if key in ndvi_by_month else None,
                }
            )
        return out

    def regional_summary(self) -> list[dict]:
        """Per-region climate averages plus NDVI start/end/change (warming and
        greening comparison across regions)."""
        climate_rows = self.db.execute(
            select(
                ClimateData.region_id,
                func.avg(ClimateData.temperature),
                func.avg(ClimateData.rainfall),
                func.avg(ClimateData.humidity),
            ).group_by(ClimateData.region_id)
        ).all()
        climate_by_region = {
            rid: (float(t) if t is not None else None,
                  float(r) if r is not None else None,
                  float(h) if h is not None else None)
            for rid, t, r, h in climate_rows
        }

        # NDVI first- vs last-month average per region.
        sm = func.date_trunc("month", SatelliteData.date)
        ndvi_rows = self.db.execute(
            select(SatelliteData.region_id, sm.label("m"), func.avg(SatelliteData.ndvi))
            .group_by(SatelliteData.region_id, "m")
            .order_by(SatelliteData.region_id, "m")
        ).all()
        ndvi_series: dict[int, list[float]] = {}
        for rid, _m, v in ndvi_rows:
            if v is not None:
                ndvi_series.setdefault(rid, []).append(float(v))

        regions = self.db.execute(select(Region.id, Region.name, Region.biome)).all()
        out: list[dict] = []
        for rid, name, biome in regions:
            temp, rain, hum = climate_by_region.get(rid, (None, None, None))
            series = ndvi_series.get(rid, [])
            ndvi_start = series[0] if series else None
            ndvi_end = series[-1] if series else None
            ndvi_change = (
                round(ndvi_end - ndvi_start, 4) if ndvi_start is not None and ndvi_end is not None else None
            )
            out.append(
                {
                    "region_id": rid,
                    "region_name": name,
                    "biome": biome,
                    "avg_temperature": round(temp, 2) if temp is not None else None,
                    "avg_rainfall": round(rain, 1) if rain is not None else None,
                    "avg_humidity": round(hum, 1) if hum is not None else None,
                    "ndvi_start": round(ndvi_start, 4) if ndvi_start is not None else None,
                    "ndvi_end": round(ndvi_end, 4) if ndvi_end is not None else None,
                    "ndvi_change": ndvi_change,
                }
            )
        out.sort(key=lambda r: (r["ndvi_change"] is None, r["ndvi_change"] or 0))
        return out
