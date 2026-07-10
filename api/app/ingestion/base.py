"""Ingestion adapter contracts (NFR-6: external integrations behind clean
interfaces). Each provider returns plain dataclass records; the IngestionService
is responsible for cleaning and persistence.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol, runtime_checkable


@dataclass
class SatelliteRecord:
    date: datetime
    ndvi: float
    location_wkt: str  # POLYGON WKT (region footprint), SRID 4326


@dataclass
class ClimateRecord:
    date: datetime
    temperature: float | None
    humidity: float | None
    rainfall: float | None
    location_wkt: str  # POLYGON WKT (region footprint), SRID 4326


@dataclass
class ObservationRecord:
    date: datetime
    scientific_name: str
    lon: float
    lat: float
    source: str
    conservation_status: str | None = None
    endemic: bool = False
    extra: dict = field(default_factory=dict)


@runtime_checkable
class SatelliteProvider(Protocol):
    name: str

    def fetch_ndvi(self, region: dict, start: datetime, end: datetime) -> list[SatelliteRecord]:
        ...


@runtime_checkable
class ClimateProvider(Protocol):
    name: str

    def fetch_climate(self, region: dict, start: datetime, end: datetime) -> list[ClimateRecord]:
        ...


@runtime_checkable
class BiodiversityProvider(Protocol):
    name: str

    def fetch_observations(self, region: dict, start: datetime, end: datetime, limit: int) -> list[ObservationRecord]:
        ...
