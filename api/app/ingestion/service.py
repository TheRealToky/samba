"""IngestionService — fetch via provider, clean, persist (FR-1).

Writes SatelliteData / ClimateData / Species + SpeciesObservation, anchored to a
Region. Species are upserted by scientific_name (SpeciesObservation.record()).
"""
from __future__ import annotations

from datetime import datetime

from geoalchemy2.elements import WKTElement
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.base import ObservationRecord
from app.ingestion.factory import (
    get_biodiversity_provider,
    get_climate_provider,
    get_satellite_provider,
)
from app.models.environmental import ClimateData, SatelliteData
from app.models.region import Region
from app.models.species import Species, SpeciesObservation
from app.processing.cleaning import clean_climate, clean_observations, clean_satellite

_SRID = 4326


def _region_dict(region: Region) -> dict:
    # bbox is recomputed from the seed definitions by code; alignment with geom.
    from app.geo.madagascar import REGIONS

    for r in REGIONS:
        if r["code"] == region.code:
            return r
    # Fallback: only code/name known (custom region) — providers still work in live mode.
    return {"code": region.code, "name": region.name, "bbox": None, "biome": region.biome}


class IngestionService:
    def __init__(self, db: Session):
        self.db = db

    # --- satellite (FR-1.1) ---------------------------------------------------
    def ingest_satellite(self, region: Region, start: datetime, end: datetime) -> int:
        provider = get_satellite_provider()
        records = clean_satellite(provider.fetch_ndvi(_region_dict(region), start, end))
        rows = [
            SatelliteData(
                location=WKTElement(r.location_wkt, srid=_SRID),
                ndvi=r.ndvi,
                date=r.date,
                region_id=region.id,
            )
            for r in records
        ]
        self.db.add_all(rows)
        self.db.commit()
        return len(rows)

    # --- climate (FR-1.2) -----------------------------------------------------
    def ingest_climate(self, region: Region, start: datetime, end: datetime) -> int:
        provider = get_climate_provider()
        records = clean_climate(provider.fetch_climate(_region_dict(region), start, end))
        rows = [
            ClimateData(
                location=WKTElement(r.location_wkt, srid=_SRID),
                temperature=r.temperature,
                humidity=r.humidity,
                rainfall=r.rainfall,
                date=r.date,
                region_id=region.id,
            )
            for r in records
        ]
        self.db.add_all(rows)
        self.db.commit()
        return len(rows)

    # --- biodiversity (FR-1, "Import species observations") -------------------
    def ingest_observations(self, region: Region, start: datetime, end: datetime, limit: int = 40) -> int:
        provider = get_biodiversity_provider()
        records = clean_observations(provider.fetch_observations(_region_dict(region), start, end, limit))
        species_cache = self._species_cache()
        rows: list[SpeciesObservation] = []
        for r in records:
            species = self._get_or_create_species(r, species_cache)
            rows.append(
                SpeciesObservation(
                    species_id=species.id,
                    location=WKTElement(f"POINT({r.lon} {r.lat})", srid=_SRID),
                    date=r.date,
                    source=r.source,
                    region_id=region.id,
                )
            )
        self.db.add_all(rows)
        self.db.commit()
        return len(rows)

    # --- helpers --------------------------------------------------------------
    def _species_cache(self) -> dict[str, Species]:
        return {s.scientific_name: s for s in self.db.execute(select(Species)).scalars().all()}

    def _get_or_create_species(self, r: ObservationRecord, cache: dict[str, Species]) -> Species:
        species = cache.get(r.scientific_name)
        if species is None:
            species = Species(
                scientific_name=r.scientific_name,
                conservation_status=r.conservation_status,
                endemic=r.endemic,
            )
            self.db.add(species)
            self.db.flush()  # assign id
            cache[r.scientific_name] = species
        elif r.conservation_status and not species.conservation_status:
            species.conservation_status = r.conservation_status
        return species
