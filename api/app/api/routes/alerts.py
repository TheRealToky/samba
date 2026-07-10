"""Environmental alert endpoints (FR-7)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.rbac import require_roles
from app.core.roles import RoleEnum
from app.db import get_db
from app.models.alert import EnvironmentalAlert
from app.models.user import User
from app.schemas.alert import AlertRead
from app.services.alert_service import AlertService

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertRead])
def list_alerts(
    alert_type: str | None = None,
    severity: str | None = None,
    acknowledged: bool | None = None,
    region_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = select(EnvironmentalAlert)
    if alert_type is not None:
        stmt = stmt.where(EnvironmentalAlert.alert_type == alert_type)
    if severity is not None:
        stmt = stmt.where(EnvironmentalAlert.severity == severity)
    if acknowledged is not None:
        stmt = stmt.where(EnvironmentalAlert.acknowledged.is_(acknowledged))
    if region_id is not None:
        stmt = stmt.where(EnvironmentalAlert.region_id == region_id)
    stmt = stmt.order_by(EnvironmentalAlert.created_at.desc())
    return list(db.execute(stmt).scalars().all())


@router.post("/generate")
def generate_alerts(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleEnum.DATA_SCIENTIST, RoleEnum.ENVIRONMENTAL_RESEARCHER)),
) -> dict:
    svc = AlertService(db)
    result = svc.generate(clear_existing=True)
    result["notified"] = svc.notify_pending()
    return result


@router.patch("/{alert_id}/acknowledge", response_model=AlertRead)
def acknowledge(
    alert_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleEnum.ENVIRONMENTAL_RESEARCHER, RoleEnum.NGO_POLICYMAKER)),
):
    alert = db.get(EnvironmentalAlert, alert_id)
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    alert.acknowledged = True
    db.commit()
    db.refresh(alert)
    return alert
