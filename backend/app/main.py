"""SAMBA MVP backend entrypoint."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import Base, engine
from .routers import analyze, auth, data, events

# Create tables on startup (MVP: no Alembic migrations yet).
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="SAMBA MVP API",
    description="System for the Administration of Malagasy Biodiversity Assessment — MVP backend.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(data.router)
app.include_router(events.router)
app.include_router(analyze.router)


@app.get("/health", tags=["meta"])
def health():
    """Public health check."""
    return {"status": "ok", "service": "samba-mvp"}
