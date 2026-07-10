"""Aggregate router for versioned endpoints, mounted under /api/v1.

Health checks are mounted at the app root (see app/main.py) so infra probes can
hit /health without a version prefix.
"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import alerts, analysis, auth, data, ingestion, regions, reports, species

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(auth.admin_router)
api_router.include_router(regions.router)
api_router.include_router(ingestion.router)
api_router.include_router(data.router)
api_router.include_router(species.router)
api_router.include_router(analysis.router)
api_router.include_router(alerts.router)
api_router.include_router(reports.router)
