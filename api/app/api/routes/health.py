"""Health checks (NFR-5). `/health` is liveness; `/health/db` is readiness."""
from __future__ import annotations

import socket

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    """Liveness: process is up. Never touches external deps.

    `instance` is the container hostname — visible through the load balancer so
    you can confirm requests are distributed across replicas.
    """
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
        "instance": socket.gethostname(),
    }


@router.get("/health/db")
def health_db(db: Session = Depends(get_db)) -> dict:
    """Readiness: DB reachable and PostGIS available."""
    db.execute(text("SELECT 1"))
    postgis_version = db.execute(text("SELECT PostGIS_Version()")).scalar_one()
    return {"status": "ok", "database": "reachable", "postgis": postgis_version}
