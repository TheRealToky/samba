"""Read endpoints for deforestation events and environmental alerts."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user

router = APIRouter(tags=["events"], dependencies=[Depends(get_current_user)])


@router.get("/events", response_model=list[schemas.DeforestationEventOut])
def list_events(
    db: Session = Depends(get_db),
    polygon_location: str | None = Query(None),
):
    stmt = select(models.DeforestationEvent)
    if polygon_location:
        stmt = stmt.where(models.DeforestationEvent.polygon_location == polygon_location)
    stmt = stmt.order_by(models.DeforestationEvent.start_date.desc())
    return db.scalars(stmt).all()


@router.get("/alerts", response_model=list[schemas.EnvironmentalAlertOut])
def list_alerts(
    db: Session = Depends(get_db),
    severity: str | None = Query(None),
):
    stmt = select(models.EnvironmentalAlert)
    if severity:
        stmt = stmt.where(models.EnvironmentalAlert.severity == severity)
    stmt = stmt.order_by(models.EnvironmentalAlert.created_at.desc())
    return db.scalars(stmt).all()
