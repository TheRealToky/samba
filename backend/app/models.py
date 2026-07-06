"""SQLAlchemy ORM models.

Field names follow the SAMBA class diagram. `polygon_location` is modelled as a
plain region-name string for the MVP (the full system stores real geometry/PostGIS).
"""
from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(50), default="researcher")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class SatelliteData(Base):
    __tablename__ = "satellite_data"

    id: Mapped[int] = mapped_column(primary_key=True)
    polygon_location: Mapped[str] = mapped_column(String(120), index=True)
    ndvi: Mapped[float] = mapped_column(Float)
    date: Mapped[date] = mapped_column(Date, index=True)


class ClimateData(Base):
    __tablename__ = "climate_data"

    id: Mapped[int] = mapped_column(primary_key=True)
    polygon_location: Mapped[str] = mapped_column(String(120), index=True)
    temperature: Mapped[float] = mapped_column(Float)
    humidity: Mapped[float] = mapped_column(Float)
    rainfall: Mapped[float] = mapped_column(Float)
    date: Mapped[date] = mapped_column(Date, index=True)


class Species(Base):
    __tablename__ = "species"

    id: Mapped[int] = mapped_column(primary_key=True)
    scientific_name: Mapped[str] = mapped_column(String(255), index=True)
    conservation_status: Mapped[str] = mapped_column(String(50))
    endemic: Mapped[bool] = mapped_column(Boolean, default=False)

    observations: Mapped[list["SpeciesObservation"]] = relationship(
        back_populates="species", cascade="all, delete-orphan"
    )


class SpeciesObservation(Base):
    __tablename__ = "species_observations"

    id: Mapped[int] = mapped_column(primary_key=True)
    polygon_location: Mapped[str] = mapped_column(String(120), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    source: Mapped[str] = mapped_column(String(120))
    species_id: Mapped[int] = mapped_column(ForeignKey("species.id"))

    species: Mapped["Species"] = relationship(back_populates="observations")


class DeforestationEvent(Base):
    __tablename__ = "deforestation_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    polygon_location: Mapped[str] = mapped_column(String(120), index=True)
    vegetation_loss: Mapped[float] = mapped_column(Float)  # percent
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    alerts: Mapped[list["EnvironmentalAlert"]] = relationship(
        back_populates="event", cascade="all, delete-orphan"
    )


class EnvironmentalAlert(Base):
    __tablename__ = "environmental_alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    severity: Mapped[str] = mapped_column(String(50))
    message: Mapped[str] = mapped_column(Text)
    linked_event_id: Mapped[int] = mapped_column(ForeignKey("deforestation_events.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    event: Mapped["DeforestationEvent"] = relationship(back_populates="alerts")
