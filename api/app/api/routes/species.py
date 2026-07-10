"""Species + observation endpoints (FR-3.2 support, "upload species photo")."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.rbac import require_roles
from app.core.roles import RoleEnum
from app.db import get_db
from app.models.user import User
from app.schemas.species import ObservationCreate, ObservationRead, SpeciesRead, StatusUpdate
from app.services.species_service import SpeciesService

router = APIRouter(prefix="/species", tags=["species"])


@router.get("", response_model=list[SpeciesRead])
def list_species(db: Session = Depends(get_db)):
    return SpeciesService(db).list_species()


@router.get("/richness")
def richness(db: Session = Depends(get_db)) -> list[dict]:
    return SpeciesService(db).richness_by_region()


@router.get("/top")
def top_observed(limit: int = 10, db: Session = Depends(get_db)) -> list[dict]:
    """Most-observed species (leaderboard)."""
    return SpeciesService(db).top_observed(limit=limit)


@router.get("/status-breakdown")
def status_breakdown(db: Session = Depends(get_db)) -> list[dict]:
    """Species + observation counts grouped by IUCN conservation status."""
    return SpeciesService(db).status_breakdown()


@router.get("/observation-trend")
def observation_trend(db: Session = Depends(get_db)) -> list[dict]:
    """Monthly observation volume, split by data source."""
    return SpeciesService(db).observation_trend()


@router.get("/observations/geojson")
def observations_geojson(limit: int = 2000, db: Session = Depends(get_db)) -> dict:
    """Observation points as GeoJSON for the biodiversity map."""
    return SpeciesService(db).observations_geojson(limit=limit)


@router.get("/decline-risk")
def decline_risk(db: Session = Depends(get_db)) -> list[dict]:
    """Species observed inside detected deforestation zones (decline watch)."""
    return SpeciesService(db).decline_risk()


@router.get("/{scientific_name}/distribution")
def distribution(scientific_name: str, db: Session = Depends(get_db)) -> list[dict]:
    return SpeciesService(db).distribution(scientific_name)


@router.post("/observations", response_model=ObservationRead, status_code=status.HTTP_201_CREATED)
def record_observation(
    payload: ObservationCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),  # any registered user
) -> ObservationRead:
    obs = SpeciesService(db).record(
        scientific_name=payload.scientific_name, lon=payload.lon, lat=payload.lat,
        source=payload.source, date=payload.date,
    )
    return ObservationRead(id=obs.id, species_id=obs.species_id, source=obs.source, date=obs.date, region_id=obs.region_id)


@router.patch("/{species_id}/status", response_model=SpeciesRead)
def update_status(
    species_id: int,
    payload: StatusUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleEnum.ENVIRONMENTAL_RESEARCHER, RoleEnum.DATA_SCIENTIST)),
):
    species = SpeciesService(db).update_status(species_id, payload.conservation_status)
    if species is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Species not found")
    return species
