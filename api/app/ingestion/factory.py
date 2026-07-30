"""Provider factory — chooses live vs sample from settings (NFR-6)."""
from __future__ import annotations

from app.config import settings
from app.ingestion.biodiversity import CompositeBiodiversityProvider
from app.ingestion.climate import NasaPowerClimateProvider
from app.ingestion.enrichment import GBIFIucnEnricher
from app.ingestion.satellite import EarthEngineSatelliteProvider


def _mode(override: str | None) -> str:
    value = (override or settings.ingestion_mode).lower()
    return "live" if value == "live" else "sample"


def get_satellite_provider() -> EarthEngineSatelliteProvider:
    return EarthEngineSatelliteProvider(mode=_mode(settings.ingestion_mode_satellite))


def get_climate_provider() -> NasaPowerClimateProvider:
    return NasaPowerClimateProvider(mode=_mode(settings.ingestion_mode_climate))


def get_biodiversity_provider() -> CompositeBiodiversityProvider:
    return CompositeBiodiversityProvider(mode=_mode(settings.ingestion_mode_biodiversity))


def get_iucn_enricher() -> GBIFIucnEnricher:
    # Auth-free default; swap for an IUCN-Red-List-API enricher here later.
    return GBIFIucnEnricher()
