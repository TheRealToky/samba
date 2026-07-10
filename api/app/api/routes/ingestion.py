"""Ingestion control (FR-1). Data scientists / admins trigger ingestion; jobs run
on the worker via the queue (or inline when run_async=False)."""
from __future__ import annotations

from datetime import datetime, time

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.rbac import require_roles
from app.core.roles import RoleEnum
from app.db import get_db
from app.models.environmental import ClimateData, SatelliteData
from app.models.region import Region
from app.models.species import Species, SpeciesObservation
from app.schemas.ingestion import IngestionRequest, JobRef

router = APIRouter(prefix="/ingestion", tags=["ingestion"])

_ingest_guard = require_roles(RoleEnum.DATA_SCIENTIST, RoleEnum.ENVIRONMENTAL_RESEARCHER)


def _dt(d) -> datetime:
    return datetime.combine(d, time.min)


@router.post("/run", response_model=JobRef, dependencies=[Depends(_ingest_guard)])
def run_ingestion(payload: IngestionRequest, db: Session = Depends(get_db)) -> JobRef:
    from app.workers import tasks
    from app.workers.queue import get_queue

    start_iso, end_iso = _dt(payload.start).isoformat(), _dt(payload.end).isoformat()

    region_id = None
    if payload.region_code:
        region_id = db.execute(
            select(Region.id).where(Region.code == payload.region_code)
        ).scalars().first()
        if region_id is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown region_code")

    if payload.run_async:
        queue = get_queue()
        if region_id is not None:
            job = queue.enqueue(tasks.ingest_region_all, region_id, start_iso, end_iso)
        else:
            job = queue.enqueue(tasks.ingest_all, start_iso, end_iso, job_timeout=1800)
        return JobRef(job_id=job.id, status="queued", detail="Ingestion job enqueued")

    # inline (blocking) — handy for quick demos / tests
    if region_id is not None:
        result = tasks.ingest_region_all(region_id, start_iso, end_iso)
    else:
        result = tasks.ingest_all(start_iso, end_iso)
    return JobRef(job_id=None, status="finished", detail="Ingestion ran inline", result=result)


@router.get("/jobs/{job_id}", response_model=JobRef, dependencies=[Depends(_ingest_guard)])
def job_status(job_id: str) -> JobRef:
    from redis import Redis
    from rq.job import Job

    from app.config import settings

    try:
        job = Job.fetch(job_id, connection=Redis.from_url(settings.redis_url))
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown job_id")
    result = job.result if job.is_finished else None
    return JobRef(
        job_id=job.id,
        status=job.get_status(),
        detail=f"Job {job.get_status()}",
        result=result if isinstance(result, dict) else ({"result": result} if result is not None else None),
    )


@router.get("/summary")
def ingestion_summary(db: Session = Depends(get_db)) -> dict:
    """Row counts per dataset — quick view of what's ingested."""
    return {
        "regions": db.scalar(select(func.count(Region.id))),
        "satellite_data": db.scalar(select(func.count(SatelliteData.id))),
        "climate_data": db.scalar(select(func.count(ClimateData.id))),
        "species": db.scalar(select(func.count(Species.id))),
        "species_observations": db.scalar(select(func.count(SpeciesObservation.id))),
    }
