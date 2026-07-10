"""Region endpoints (list + GeoJSON for the map)."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from geoalchemy2.functions import ST_AsGeoJSON
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.region import Region
from app.schemas.region import RegionRead

router = APIRouter(prefix="/regions", tags=["regions"])


@router.get("", response_model=list[RegionRead])
def list_regions(db: Session = Depends(get_db)) -> list[Region]:
    return list(db.execute(select(Region).order_by(Region.name)).scalars().all())


@router.get("/geojson")
def regions_geojson(db: Session = Depends(get_db)) -> dict:
    """FeatureCollection of region polygons for the interactive map (FR-4.1)."""
    rows = db.execute(
        select(Region.code, Region.name, Region.biome, ST_AsGeoJSON(Region.geom))
    ).all()
    features = [
        {
            "type": "Feature",
            "properties": {"code": c, "name": n, "biome": b},
            "geometry": json.loads(g),
        }
        for c, n, b, g in rows
    ]
    return {"type": "FeatureCollection", "features": features}
