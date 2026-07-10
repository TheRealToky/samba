"""Queue tasks executed by the worker (FR-1, FR-2).

Each task opens its own DB session (workers are separate processes). Dates are
passed as ISO strings so they serialize cleanly onto the queue.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.db import SessionLocal
from app.geo.madagascar import REGIONS
from app.ingestion.service import IngestionService
from app.models.region import Region
from sqlalchemy import select


def ping() -> str:
    return "pong"


def _parse(dt_iso: str) -> datetime:
    dt = datetime.fromisoformat(dt_iso)
    if dt.tzinfo is None:  # keep everything UTC-aware (columns are timestamptz)
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def ingest_satellite_task(region_id: int, start_iso: str, end_iso: str) -> int:
    with SessionLocal() as db:
        region = db.get(Region, region_id)
        if region is None:
            return 0
        return IngestionService(db).ingest_satellite(region, _parse(start_iso), _parse(end_iso))


def ingest_climate_task(region_id: int, start_iso: str, end_iso: str) -> int:
    with SessionLocal() as db:
        region = db.get(Region, region_id)
        if region is None:
            return 0
        return IngestionService(db).ingest_climate(region, _parse(start_iso), _parse(end_iso))


def ingest_observations_task(region_id: int, start_iso: str, end_iso: str, limit: int = 40) -> int:
    with SessionLocal() as db:
        region = db.get(Region, region_id)
        if region is None:
            return 0
        return IngestionService(db).ingest_observations(region, _parse(start_iso), _parse(end_iso), limit)


def ingest_region_all(region_id: int, start_iso: str, end_iso: str) -> dict:
    return {
        "satellite": ingest_satellite_task(region_id, start_iso, end_iso),
        "climate": ingest_climate_task(region_id, start_iso, end_iso),
        "observations": ingest_observations_task(region_id, start_iso, end_iso),
    }


def train_models_task() -> dict:
    """Run the full training pipeline, then reload the inference server."""
    import httpx

    from app.config import settings
    from app.ml.train import main as train_main

    train_main()
    try:
        httpx.post(f"{settings.inference_url}/reload", timeout=30)
    except Exception as exc:  # inference reload is best-effort
        print(f"[train task] inference reload failed: {exc}", flush=True)
    return {"status": "trained"}


def ingest_all(start_iso: str, end_iso: str) -> dict:
    """Synchronous full ingestion across every region (used by the demo button)."""
    totals = {"satellite": 0, "climate": 0, "observations": 0, "regions": 0}
    with SessionLocal() as db:
        region_ids = list(db.execute(select(Region.id)).scalars().all())
    for rid in region_ids:
        result = ingest_region_all(rid, start_iso, end_iso)
        for k, v in result.items():
            totals[k] += v
        totals["regions"] += 1
    return totals
