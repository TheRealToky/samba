"""Analysis + ML endpoints (FR-3 outputs, "Access unified API", "Train ML models")."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from geoalchemy2.functions import ST_AsGeoJSON
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.core.deps import get_current_user
from app.core.rbac import require_roles
from app.core.roles import RoleEnum
from app.db import get_db
from app.models.ml import DeforestationEvent, MLModel, PredictionResult
from app.models.user import User

router = APIRouter(tags=["analysis"])


@router.get("/deforestation-events")
def list_deforestation_events(region_id: int | None = None, db: Session = Depends(get_db)) -> list[dict]:
    stmt = select(
        DeforestationEvent.id, DeforestationEvent.vegetation_loss,
        DeforestationEvent.start_date, DeforestationEvent.end_date,
        DeforestationEvent.region_id, ST_AsGeoJSON(DeforestationEvent.location),
    )
    if region_id is not None:
        stmt = stmt.where(DeforestationEvent.region_id == region_id)
    stmt = stmt.order_by(DeforestationEvent.vegetation_loss.desc())
    return [
        {
            "id": i, "vegetation_loss": float(v), "start_date": s, "end_date": e,
            "region_id": rid, "geometry": json.loads(g) if g else None,
        }
        for i, v, s, e, rid, g in db.execute(stmt).all()
    ]


@router.get("/predictions")
def list_predictions(
    type: str | None = None, region_id: int | None = None, limit: int = 500, db: Session = Depends(get_db)
) -> list[dict]:
    stmt = select(PredictionResult)
    if type is not None:
        stmt = stmt.where(PredictionResult.type == type)
    if region_id is not None:
        stmt = stmt.where(PredictionResult.region_id == region_id)
    stmt = stmt.order_by(PredictionResult.date.desc()).limit(limit)
    return [
        {
            "id": p.id, "type": p.type, "confidence": p.confidence, "date": p.date,
            "region_id": p.region_id, "ml_model_id": p.ml_model_id, "payload": p.payload,
        }
        for p in db.execute(stmt).scalars().all()
    ]


@router.get("/models")
def list_models(db: Session = Depends(get_db)) -> list[dict]:
    return [
        {"id": m.id, "name": m.name, "hyperparameters": m.hyperparameters, "created_at": m.created_at}
        for m in db.execute(select(MLModel).order_by(MLModel.name)).scalars().all()
    ]


class PredictRequest(BaseModel):
    model: str
    features: dict = {}


@router.post("/ml/predict")
def ml_predict(payload: PredictRequest, _: User = Depends(get_current_user)) -> dict:
    """Proxy to the decoupled inference server (deployment diagram)."""
    import httpx

    try:
        resp = httpx.post(
            f"{settings.inference_url}/predict",
            json={"model": payload.model, "features": payload.features},
            timeout=30,
        )
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Inference server error: {exc}")
    return resp.json()


@router.post("/ml/train")
def trigger_training(
    _: User = Depends(require_roles(RoleEnum.DATA_SCIENTIST)),
) -> dict:
    """Enqueue a training run on the worker (data scientists / admins)."""
    from app.workers import tasks
    from app.workers.queue import get_queue

    job = get_queue().enqueue(tasks.train_models_task, job_timeout=1800)
    return {"job_id": job.id, "status": "queued", "detail": "Training job enqueued"}
