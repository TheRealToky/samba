"""Model package — importing everything here ensures every table is registered
on ``Base.metadata`` (used by Alembic autogenerate and tests)."""
from app.models.base import Base
from app.models.user import User
from app.models.region import Region
from app.models.environmental import SatelliteData, ClimateData
from app.models.species import Species, SpeciesObservation
from app.models.ml import MLModel, PredictionResult, DeforestationEvent
from app.models.alert import EnvironmentalAlert
from app.models.report import Report

__all__ = [
    "Base",
    "User",
    "Region",
    "SatelliteData",
    "ClimateData",
    "Species",
    "SpeciesObservation",
    "MLModel",
    "PredictionResult",
    "DeforestationEvent",
    "EnvironmentalAlert",
    "Report",
]
