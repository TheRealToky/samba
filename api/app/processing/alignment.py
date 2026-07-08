"""Spatial-temporal alignment (FR-2.2): match datasets by region + time bucket.

Produces the aligned per-region monthly feature table that the ML stage trains
on. Because ingested rows carry a region_id and a timestamp, alignment is an
indexed group-by rather than an expensive spatial join (NFR-2).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Integer, func, select
from sqlalchemy.orm import Session

from app.models.environmental import ClimateData, SatelliteData
from app.models.species import SpeciesObservation


@dataclass
class AlignedRow:
    period: datetime
    ndvi: float | None
    temperature: float | None
    rainfall: float | None
    humidity: float | None
    observation_count: int
    species_richness: int


def _month(col):
    return func.date_trunc("month", col)


def ndvi_series(db: Session, region_id: int) -> list[tuple[datetime, float]]:
    """Ordered NDVI time series for a region (input to change-point detection)."""
    rows = db.execute(
        select(SatelliteData.date, SatelliteData.ndvi)
        .where(SatelliteData.region_id == region_id)
        .order_by(SatelliteData.date)
    ).all()
    return [(d, float(v)) for d, v in rows]


def align_region(db: Session, region_id: int, start: datetime | None = None, end: datetime | None = None) -> list[AlignedRow]:
    # Build each period expression ONCE and reuse it in SELECT + GROUP BY so
    # Postgres sees identical expressions (bind params must match).
    sat_period = _month(SatelliteData.date)
    sat = {
        p: n
        for p, n in db.execute(
            select(sat_period, func.avg(SatelliteData.ndvi))
            .where(SatelliteData.region_id == region_id)
            .group_by(sat_period)
        ).all()
    }
    clim_period = _month(ClimateData.date)
    clim = {
        p: (t, r, h)
        for p, t, r, h in db.execute(
            select(
                clim_period,
                func.avg(ClimateData.temperature),
                func.avg(ClimateData.rainfall),
                func.avg(ClimateData.humidity),
            )
            .where(ClimateData.region_id == region_id)
            .group_by(clim_period)
        ).all()
    }
    obs_period = _month(SpeciesObservation.date)
    obs = {
        p: (cnt, rich)
        for p, cnt, rich in db.execute(
            select(
                obs_period,
                func.count(SpeciesObservation.id),
                func.count(func.distinct(SpeciesObservation.species_id)).cast(Integer),
            )
            .where(SpeciesObservation.region_id == region_id)
            .group_by(obs_period)
        ).all()
    }

    periods = sorted(set(sat) | set(clim) | set(obs))
    if start:
        periods = [p for p in periods if p >= start]
    if end:
        periods = [p for p in periods if p <= end]

    out: list[AlignedRow] = []
    for p in periods:
        t, r, h = clim.get(p, (None, None, None))
        cnt, rich = obs.get(p, (0, 0))
        out.append(
            AlignedRow(
                period=p,
                ndvi=float(sat[p]) if p in sat and sat[p] is not None else None,
                temperature=float(t) if t is not None else None,
                rainfall=float(r) if r is not None else None,
                humidity=float(h) if h is not None else None,
                observation_count=int(cnt or 0),
                species_richness=int(rich or 0),
            )
        )
    return out
