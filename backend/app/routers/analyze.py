"""POST /analyze — scan SatelliteData for NDVI drops and create events + alerts.

Re-runs are idempotent for demo purposes: previously generated DeforestationEvents
(and their linked EnvironmentalAlerts, via cascade) are cleared first, then the
detector re-computes from scratch. A production system would dedupe/version events
instead of wiping them.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..config import settings
from ..database import get_db
from ..deps import get_current_user
from ..detection import NDVIPoint, detect_region_events, severity_for_loss

router = APIRouter(tags=["analyze"], dependencies=[Depends(get_current_user)])


@router.post("/analyze", response_model=schemas.AnalyzeResult)
def analyze(db: Session = Depends(get_db)):
    # Clear prior generated events; alerts cascade-delete with their event.
    for ev in db.scalars(select(models.DeforestationEvent)).all():
        db.delete(ev)
    db.flush()

    locations = db.scalars(
        select(models.SatelliteData.polygon_location).distinct()
    ).all()

    created_events: list[models.DeforestationEvent] = []
    alerts_created = 0

    for loc in locations:
        rows = db.scalars(
            select(models.SatelliteData)
            .where(models.SatelliteData.polygon_location == loc)
            .order_by(models.SatelliteData.date)
        ).all()
        points = [NDVIPoint(date=r.date, ndvi=r.ndvi) for r in rows]

        detected = detect_region_events(
            polygon_location=loc,
            points=points,
            drop_threshold_pct=settings.ndvi_drop_threshold_pct,
            window_days=settings.detection_window_days,
        )

        for d in detected:
            event = models.DeforestationEvent(
                polygon_location=d.polygon_location,
                vegetation_loss=d.vegetation_loss,
                start_date=d.start_date,
                end_date=d.end_date,
            )
            db.add(event)
            db.flush()  # assign event.id for the FK

            severity = severity_for_loss(d.vegetation_loss)
            message = (
                f"{severity.capitalize()} deforestation in {d.polygon_location}: "
                f"{d.vegetation_loss:.1f}% NDVI loss between "
                f"{d.start_date.isoformat()} and {d.end_date.isoformat()}."
            )
            db.add(
                models.EnvironmentalAlert(
                    severity=severity,
                    message=message,
                    linked_event_id=event.id,
                )
            )
            alerts_created += 1
            created_events.append(event)

    db.commit()
    for ev in created_events:
        db.refresh(ev)

    return schemas.AnalyzeResult(
        regions_scanned=len(locations),
        events_created=len(created_events),
        alerts_created=alerts_created,
        events=created_events,
    )
