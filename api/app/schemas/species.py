from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SpeciesRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scientific_name: str
    conservation_status: str | None = None
    endemic: bool


class ObservationCreate(BaseModel):
    scientific_name: str = Field(min_length=1)
    lon: float = Field(ge=-180, le=180)
    lat: float = Field(ge=-90, le=90)
    date: datetime | None = None
    source: str = "upload"


class ObservationRead(BaseModel):
    id: int
    species_id: int
    source: str
    date: datetime
    region_id: int | None = None


class StatusUpdate(BaseModel):
    conservation_status: str
