"""SAMBA backend API entrypoint.

Corresponds to the "Backend API" node in the deployment diagram: it fronts
PostGIS, object storage, and the ML inference server, and sits behind the load
balancer's web-server replicas.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.api.routes import health
from app.config import settings

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="System for the Administration of Malagasy Biodiversity Assessment",
)

# CORS — permissive in dev; tighten to the web origin in Phase 6.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health at root (infra probes), everything else under /api/v1.
app.include_router(health.router)
app.include_router(api_router, prefix="/api/v1")


@app.get("/", tags=["meta"])
def root() -> dict:
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
    }
