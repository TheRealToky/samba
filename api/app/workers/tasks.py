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


def ingest_observations_task(region_id: int, start_iso: str, end_iso: str, limit: int | None = None) -> int:
    from app.config import settings

    if limit is None:
        # Live pulls paginate up to this cap; sample ingestion caps at 40 internally.
        limit = settings.biodiversity_max_records
    with SessionLocal() as db:
        region = db.get(Region, region_id)
        if region is None:
            return 0
        return IngestionService(db).ingest_observations(region, _parse(start_iso), _parse(end_iso), limit)


def ingest_region_all(region_id: int, start_iso: str, end_iso: str, limit: int | None = None) -> dict:
    return {
        "satellite": ingest_satellite_task(region_id, start_iso, end_iso),
        "climate": ingest_climate_task(region_id, start_iso, end_iso),
        "observations": ingest_observations_task(region_id, start_iso, end_iso, limit),
    }


def enrich_species_task(limit: int | None = None) -> dict:
    """Fill Species.conservation_status via IUCN enrichment (Stage 3).

    Skipped in sample mode (sample species already carry a status) and when
    disabled by config."""
    from app.config import settings
    from app.ingestion.factory import _mode, get_iucn_enricher
    from app.services.enrichment_service import EnrichmentService

    if not settings.iucn_enrichment_enabled:
        return {"skipped": "disabled", "checked": 0, "enriched": 0}
    if _mode(settings.ingestion_mode_biodiversity) != "live":
        return {"skipped": "sample_mode", "checked": 0, "enriched": 0}
    with SessionLocal() as db:
        return EnrichmentService(db, get_iucn_enricher()).enrich_missing(limit)


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


def ingest_all(start_iso: str, end_iso: str, limit: int | None = None) -> dict:
    """Synchronous full ingestion across every region (used by the demo button)."""
    totals = {"satellite": 0, "climate": 0, "observations": 0, "regions": 0}
    with SessionLocal() as db:
        region_ids = list(db.execute(select(Region.id)).scalars().all())
    for rid in region_ids:
        result = ingest_region_all(rid, start_iso, end_iso, limit)
        for k, v in result.items():
            totals[k] += v
        totals["regions"] += 1
    # Second pass: resolve IUCN status for newly-seen species (no-op in sample mode).
    totals["enriched"] = enrich_species_task().get("enriched", 0)
    return totals
