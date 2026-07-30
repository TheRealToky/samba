"""IngestionService — fetch via provider, clean, persist (FR-1).

Writes SatelliteData / ClimateData / Species + SpeciesObservation, anchored to a
Region. Species are upserted by scientific_name (SpeciesObservation.record()).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
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


def _geom(wkt: str):
    """WKT -> PostGIS geometry expression usable in a Core (multi-row) insert."""
    return func.ST_GeomFromEWKT(f"SRID={_SRID};{wkt}")


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
        if not records:
            return 0
        values = [
            {
                "location": _geom(r.location_wkt),
                "ndvi": r.ndvi,
                "date": r.date,
                "region_id": region.id,
            }
            for r in records
        ]
        stmt = pg_insert(SatelliteData).values(values)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_satellite_data_region_date",
            set_={"ndvi": stmt.excluded.ndvi, "location": stmt.excluded.location},
        )
        self.db.execute(stmt)
        self.db.commit()
        return len(values)

    # --- climate (FR-1.2) -----------------------------------------------------
    def ingest_climate(self, region: Region, start: datetime, end: datetime) -> int:
        provider = get_climate_provider()
        records = clean_climate(provider.fetch_climate(_region_dict(region), start, end))
        if not records:
            return 0
        values = [
            {
                "location": _geom(r.location_wkt),
                "temperature": r.temperature,
                "humidity": r.humidity,
                "rainfall": r.rainfall,
                "date": r.date,
                "region_id": region.id,
            }
            for r in records
        ]
        stmt = pg_insert(ClimateData).values(values)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_climate_data_region_date",
            set_={
                "temperature": stmt.excluded.temperature,
                "humidity": stmt.excluded.humidity,
                "rainfall": stmt.excluded.rainfall,
                "location": stmt.excluded.location,
            },
        )
        self.db.execute(stmt)
        self.db.commit()
        return len(values)

    # --- biodiversity (FR-1, "Import species observations") -------------------
    def ingest_observations(self, region: Region, start: datetime, end: datetime, limit: int = 40) -> int:
        provider = get_biodiversity_provider()
        records = clean_observations(provider.fetch_observations(_region_dict(region), start, end, limit))
        if not records:
            return 0
        species_cache = self._species_cache()
        values = []
        for r in records:
            species = self._get_or_create_species(r, species_cache)
            ext = r.extra.get("gbif_key") or r.extra.get("inat_id")
            values.append(
                {
                    "species_id": species.id,
                    "location": _geom(f"POINT({r.lon} {r.lat})"),
                    "date": r.date,
                    "source": r.source,
                    "external_id": str(ext) if ext is not None else None,
                    "region_id": region.id,
                }
            )
        # Skip records already stored (same provider occurrence id). NULL
        # external_id rows (sample data) never conflict and always insert.
        stmt = pg_insert(SpeciesObservation).values(values)
        stmt = stmt.on_conflict_do_nothing(constraint="uq_species_obs_source_external")
        self.db.execute(stmt)
        self.db.commit()
        return len(values)

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
