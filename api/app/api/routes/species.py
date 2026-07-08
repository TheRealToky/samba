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
