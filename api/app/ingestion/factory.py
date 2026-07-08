"""Provider factory — chooses live vs sample from settings (NFR-6)."""
from __future__ import annotations

from app.config import settings
from app.ingestion.biodiversity import CompositeBiodiversityProvider
from app.ingestion.climate import NasaPowerClimateProvider
from app.ingestion.satellite import EarthEngineSatelliteProvider


def _mode() -> str:
    return "live" if settings.ingestion_mode.lower() == "live" else "sample"


def get_satellite_provider() -> EarthEngineSatelliteProvider:
    return EarthEngineSatelliteProvider(mode=_mode())


def get_climate_provider() -> NasaPowerClimateProvider:
    return NasaPowerClimateProvider(mode=_mode())


def get_biodiversity_provider() -> CompositeBiodiversityProvider:
    return CompositeBiodiversityProvider(mode=_mode())
