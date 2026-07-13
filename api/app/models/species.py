"""Taxonomy + observations (class diagram: Species, SpeciesObservation).

Relationship: Species 1 --- * SpeciesObservation.

NOTE (deviation from class diagram, flagged intentionally): the diagram shows
`SpeciesObservation.location` as a polygon, but real occurrence records from
GBIF / iNaturalist are point coordinates. We store a POINT here so ingested data
is faithful; region-level aggregation happens via spatial joins in Phase 2.
"""
from __future__ import annotations

from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Species(Base, TimestampMixin):
    __tablename__ = "species"

    id: Mapped[int] = mapped_column(primary_key=True)
    scientific_name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    conservation_status: Mapped[str | None] = mapped_column(String(100), nullable=True)
    endemic: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)

    observations: Mapped[list["SpeciesObservation"]] = relationship(
        back_populates="species", cascade="all, delete-orphan"
    )


class SpeciesObservation(Base, TimestampMixin):
    __tablename__ = "species_observations"
    # (source, external_id) is the provider's own occurrence id (GBIF key /
    # iNaturalist id), so re-ingesting an overlapping window doesn't duplicate
    # records. NULL external_id (e.g. sample data) is exempt — Postgres treats
    # NULLs as distinct — which is fine since sample data is ingested once.
    __table_args__ = (UniqueConstraint("source", "external_id", name="uq_species_obs_source_external"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    species_id: Mapped[int] = mapped_column(ForeignKey("species.id", ondelete="CASCADE"), index=True)
    location = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=True), nullable=False
    )
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g. "gbif", "inaturalist"
    # Provider-native occurrence id (GBIF occurrence key / iNaturalist obs id).
    external_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    region_id: Mapped[int | None] = mapped_column(
        ForeignKey("regions.id", ondelete="SET NULL"), index=True, nullable=True
    )

    species: Mapped["Species"] = relationship(back_populates="observations")
