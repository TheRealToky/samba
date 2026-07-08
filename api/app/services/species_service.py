"""Species services.

Implements SpeciesObservation.record() (single upload — the "upload species
photo" use case) and Species.updateStatus(), plus distribution queries used by
the dashboard and SDM.
"""
from __future__ import annotations

from datetime import datetime, timezone

from geoalchemy2.elements import WKTElement
from geoalchemy2.functions import ST_AsGeoJSON, ST_Contains
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.region import Region
from app.models.species import Species, SpeciesObservation


class SpeciesService:
    def __init__(self, db: Session):
        self.db = db

    # Species.updateStatus()
    def update_status(self, species_id: int, conservation_status: str) -> Species | None:
        species = self.db.get(Species, species_id)
        if species is None:
            return None
        species.conservation_status = conservation_status
        self.db.commit()
        self.db.refresh(species)
        return species

    def get_or_create(self, scientific_name: str, conservation_status: str | None = None, endemic: bool = False) -> Species:
        species = self.db.execute(
            select(Species).where(Species.scientific_name == scientific_name)
        ).scalar_one_or_none()
        if species is None:
            species = Species(
                scientific_name=scientific_name, conservation_status=conservation_status, endemic=endemic
            )
            self.db.add(species)
            self.db.commit()
            self.db.refresh(species)
        return species

    # SpeciesObservation.record()
    def record(self, scientific_name: str, lon: float, lat: float, source: str = "upload", date: datetime | None = None) -> SpeciesObservation:
        species = self.get_or_create(scientific_name)
        region_id = self._region_for_point(lon, lat)
        obs = SpeciesObservation(
            species_id=species.id,
            location=WKTElement(f"POINT({lon} {lat})", srid=4326),
            date=date or datetime.now(timezone.utc),
            source=source,
            region_id=region_id,
        )
        self.db.add(obs)
        self.db.commit()
        self.db.refresh(obs)
        return obs

    def _region_for_point(self, lon: float, lat: float) -> int | None:
        return self.db.execute(
            select(Region.id).where(ST_Contains(Region.geom, WKTElement(f"POINT({lon} {lat})", srid=4326)))
        ).scalars().first()

    # Distribution: observation counts per region for a species (FR-3.2 support).
    def distribution(self, scientific_name: str) -> list[dict]:
        rows = self.db.execute(
            select(Region.code, Region.name, func.count(SpeciesObservation.id))
            .join(SpeciesObservation, SpeciesObservation.region_id == Region.id)
            .join(Species, Species.id == SpeciesObservation.species_id)
            .where(Species.scientific_name == scientific_name)
            .group_by(Region.code, Region.name)
            .order_by(func.count(SpeciesObservation.id).desc())
        ).all()
        return [{"region_code": c, "region_name": n, "count": int(cnt)} for c, n, cnt in rows]

    def richness_by_region(self) -> list[dict]:
        rows = self.db.execute(
            select(
                Region.code, Region.name,
                func.count(func.distinct(SpeciesObservation.species_id)),
                func.count(SpeciesObservation.id),
            )
            .join(SpeciesObservation, SpeciesObservation.region_id == Region.id)
            .group_by(Region.code, Region.name)
            .order_by(Region.name)
        ).all()
        return [
            {"region_code": c, "region_name": n, "species_richness": int(rich), "observations": int(cnt)}
            for c, n, rich, cnt in rows
        ]

    def list_species(self) -> list[Species]:
        return list(self.db.execute(select(Species).order_by(Species.scientific_name)).scalars().all())
