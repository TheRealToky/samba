"""ML Inference Server (deployment-diagram node), decoupled from training.
Runs as: uvicorn app.inference.app:app --port 9000

Loads model artifacts published by the training server (Phase 3) from object
storage / the shared model dir. Falls back to a deterministic stub for any model
that isn't loaded yet, so the API always has a stable contract to call.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.ml.registry import ModelRegistry

app = FastAPI(title="SAMBA Inference Server", version="0.2.0")
registry = ModelRegistry()


class PredictRequest(BaseModel):
    model: str = Field(description="Model family: 'deforestation' | 'sdm' | 'climate'")
    features: dict = Field(default_factory=dict)


class PredictResponse(BaseModel):
    model: str
    type: str
    confidence: float
    prediction: dict
    served_by: str
    served_at: datetime


@app.on_event("startup")
def _load() -> None:
    registry.load_all()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "inference", "loaded_models": registry.loaded_names()}


@app.get("/models")
def models() -> dict:
    return {"models": registry.describe()}


@app.post("/reload")
def reload_models() -> dict:
    """Reload artifacts from the model store (call after a training run)."""
    registry.load_all()
    return {"status": "reloaded", "loaded_models": registry.loaded_names()}


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest) -> PredictResponse:
    result = registry.predict(req.model, req.features)
    return PredictResponse(
        model=req.model,
        type=result["type"],
        confidence=result["confidence"],
        prediction=result["prediction"],
        served_by=result["served_by"],
        served_at=datetime.now(timezone.utc),
    )
