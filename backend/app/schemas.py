"""Pydantic request/response schemas."""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr


# ---- Auth ----
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: EmailStr
    role: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---- Environmental data ----
class SatelliteDataOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    polygon_location: str
    ndvi: float
    date: date


class ClimateDataOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    polygon_location: str
    temperature: float
    humidity: float
    rainfall: float
    date: date


class SpeciesOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    scientific_name: str
    conservation_status: str
    endemic: bool


class SpeciesObservationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    polygon_location: str
    date: date
    source: str
    species_id: int


# ---- Events & alerts ----
class DeforestationEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    polygon_location: str
    vegetation_loss: float
    start_date: date
    end_date: date
    created_at: datetime


class EnvironmentalAlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    severity: str
    message: str
    linked_event_id: int
    created_at: datetime


# ---- Aggregates for the dashboard ----
class NDVITrendPoint(BaseModel):
    date: date
    ndvi: float


class RegionSummary(BaseModel):
    polygon_location: str
    latest_ndvi: float | None
    latest_date: date | None
    trend: list[NDVITrendPoint]
    has_active_event: bool
    max_severity: str | None


class AnalyzeResult(BaseModel):
    regions_scanned: int
    events_created: int
    alerts_created: int
    events: list[DeforestationEventOut]
