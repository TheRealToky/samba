"""Read/query endpoints for environmental data + a dashboard region summary.

All routes require a logged-in researcher.
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user

router = APIRouter(tags=["data"], dependencies=[Depends(get_current_user)])


def _date_filter(stmt, model, start: date | None, end: date | None):
    if start is not None:
        stmt = stmt.where(model.date >= start)
    if end is not None:
        stmt = stmt.where(model.date <= end)
    return stmt


@router.get("/satellite", response_model=list[schemas.SatelliteDataOut])
def list_satellite(
    db: Session = Depends(get_db),
    polygon_location: str | None = Query(None),
    start: date | None = Query(None),
    end: date | None = Query(None),
):
    stmt = select(models.SatelliteData)
    if polygon_location:
        stmt = stmt.where(models.SatelliteData.polygon_location == polygon_location)
    stmt = _date_filter(stmt, models.SatelliteData, start, end)
    stmt = stmt.order_by(models.SatelliteData.date)
    return db.scalars(stmt).all()


@router.get("/climate", response_model=list[schemas.ClimateDataOut])
def list_climate(
    db: Session = Depends(get_db),
    polygon_location: str | None = Query(None),
    start: date | None = Query(None),
    end: date | None = Query(None),
):
    stmt = select(models.ClimateData)
    if polygon_location:
        stmt = stmt.where(models.ClimateData.polygon_location == polygon_location)
    stmt = _date_filter(stmt, models.ClimateData, start, end)
    stmt = stmt.order_by(models.ClimateData.date)
    return db.scalars(stmt).all()


@router.get("/species", response_model=list[schemas.SpeciesOut])
def list_species(db: Session = Depends(get_db)):
    return db.scalars(select(models.Species).order_by(models.Species.scientific_name)).all()


@router.get("/observations", response_model=list[schemas.SpeciesObservationOut])
def list_observations(
    db: Session = Depends(get_db),
    polygon_location: str | None = Query(None),
    species_id: int | None = Query(None),
):
    stmt = select(models.SpeciesObservation)
    if polygon_location:
        stmt = stmt.where(models.SpeciesObservation.polygon_location == polygon_location)
    if species_id:
        stmt = stmt.where(models.SpeciesObservation.species_id == species_id)
    stmt = stmt.order_by(models.SpeciesObservation.date)
    return db.scalars(stmt).all()


@router.get("/regions", response_model=list[schemas.RegionSummary])
def region_summary(db: Session = Depends(get_db)):
    """Per-region aggregate used by the dashboard: NDVI trend + active-event state."""
    severity_rank = {"moderate": 1, "high": 2, "critical": 3}

    locations = db.scalars(
        select(models.SatelliteData.polygon_location).distinct()
    ).all()

    summaries: list[schemas.RegionSummary] = []
    for loc in sorted(locations):
        points = db.scalars(
            select(models.SatelliteData)
            .where(models.SatelliteData.polygon_location == loc)
            .order_by(models.SatelliteData.date)
        ).all()
        trend = [schemas.NDVITrendPoint(date=p.date, ndvi=p.ndvi) for p in points]

        # Active events + their alert severities for this region.
        events = db.scalars(
            select(models.DeforestationEvent).where(
                models.DeforestationEvent.polygon_location == loc
            )
        ).all()
        max_severity = None
        for ev in events:
            for alert in ev.alerts:
                if max_severity is None or severity_rank.get(alert.severity, 0) > severity_rank.get(max_severity, 0):
                    max_severity = alert.severity

        summaries.append(
            schemas.RegionSummary(
                polygon_location=loc,
                latest_ndvi=points[-1].ndvi if points else None,
                latest_date=points[-1].date if points else None,
                trend=trend,
                has_active_event=bool(events),
                max_severity=max_severity,
            )
        )
    return summaries
