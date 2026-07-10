"""Environmental data query endpoints (FR-1/FR-2 read side)."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.processing.alignment import align_region, ndvi_series
from app.services.data_service import ClimateAnalyticsService, ClimateService, SatelliteService

router = APIRouter(tags=["data"])


def _parse_bbox(bbox: str | None) -> tuple[float, float, float, float] | None:
    if not bbox:
        return None
    try:
        parts = tuple(float(x) for x in bbox.split(","))
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="bbox must be lon_min,lat_min,lon_max,lat_max")
    if len(parts) != 4:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="bbox needs 4 numbers")
    return parts  # type: ignore[return-value]


@router.get("/satellite")
def query_satellite(
    region_id: int | None = None,
    bbox: str | None = Query(default=None, description="lon_min,lat_min,lon_max,lat_max"),
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = Query(default=1000, le=5000),
    db: Session = Depends(get_db),
) -> list[dict]:
    return SatelliteService(db).query(region_id=region_id, bbox=_parse_bbox(bbox), start=start, end=end, limit=limit)


@router.get("/climate")
def query_climate(
    region_id: int | None = None,
    bbox: str | None = Query(default=None, description="lon_min,lat_min,lon_max,lat_max"),
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = Query(default=1000, le=5000),
    db: Session = Depends(get_db),
) -> list[dict]:
    return ClimateService(db).query(region_id=region_id, bbox=_parse_bbox(bbox), start=start, end=end, limit=limit)


@router.get("/climate/overview")
def climate_overview(db: Session = Depends(get_db)) -> list[dict]:
    """National monthly climate + vegetation trend (temp/rainfall/humidity/NDVI)."""
    return ClimateAnalyticsService(db).national_monthly()


@router.get("/climate/regional")
def climate_regional(db: Session = Depends(get_db)) -> list[dict]:
    """Per-region climate averages + NDVI change for cross-region comparison."""
    return ClimateAnalyticsService(db).regional_summary()


@router.get("/regions/{region_id}/ndvi-series")
def region_ndvi_series(region_id: int, db: Session = Depends(get_db)) -> dict:
    series = ndvi_series(db, region_id)
    return {"region_id": region_id, "points": [{"date": d, "ndvi": v} for d, v in series]}


@router.get("/regions/{region_id}/alignment")
def region_alignment(region_id: int, db: Session = Depends(get_db)) -> dict:
    rows = align_region(db, region_id)
    return {
        "region_id": region_id,
        "rows": [
            {
                "period": r.period, "ndvi": r.ndvi, "temperature": r.temperature,
                "rainfall": r.rainfall, "humidity": r.humidity,
                "observation_count": r.observation_count, "species_richness": r.species_richness,
            }
            for r in rows
        ],
    }
