"""Report endpoints (FR-5): generate, list, download (CSV/PDF)."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db import get_db
from app.models.report import Report
from app.models.user import User
from app.services.report_service import ReportService
from app.storage.objectstore import get_bytes

router = APIRouter(prefix="/reports", tags=["reports"])

_MEDIA = {"csv": "text/csv", "pdf": "application/pdf"}


class ReportCreate(BaseModel):
    format: str = "csv"
    params: dict = {}


class ReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    format: str
    object_key: str | None
    user_id: int | None
    created_at: datetime


@router.post("", response_model=ReportRead, status_code=status.HTTP_201_CREATED)
def create_report(
    payload: ReportCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Report:
    try:
        return ReportService(db).generate(fmt=payload.format, user_id=user.id, params=payload.params)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.get("", response_model=list[ReportRead])
def list_reports(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return list(db.execute(select(Report).order_by(Report.created_at.desc())).scalars().all())


@router.get("/{report_id}/download")
def download_report(report_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    report = db.get(Report, report_id)
    if report is None or not report.object_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    try:
        data = get_bytes(report.object_key)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Object storage error: {exc}")
    filename = f"samba_report_{report.id}.{report.format}"
    return Response(
        content=data,
        media_type=_MEDIA.get(report.format, "application/octet-stream"),
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
