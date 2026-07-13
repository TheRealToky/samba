"""Environmental datasets (class diagram: SatelliteData, ClimateData).

Both carry a PostGIS polygon `location` (region footprint) plus a timestamp, so
they can be spatially/temporally aligned in Phase 2. GiST spatial indexes are
declared from day one (NFR-2).
"""
from __future__ import annotations

from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class SatelliteData(Base, TimestampMixin):
    __tablename__ = "satellite_data"
    # One NDVI reading per region per timestamp — lets ingestion upsert instead
    # of duplicating rows when a date window is re-ingested (live/scheduled runs).
    __table_args__ = (UniqueConstraint("region_id", "date", name="uq_satellite_data_region_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    location = mapped_column(
        Geometry(geometry_type="POLYGON", srid=4326, spatial_index=True), nullable=False
    )
    ndvi: Mapped[float] = mapped_column(Float, nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    # Pragmatic addition: link to a Region for cheap grouping/alignment.
    region_id: Mapped[int | None] = mapped_column(
        ForeignKey("regions.id", ondelete="SET NULL"), index=True, nullable=True
    )


class ClimateData(Base, TimestampMixin):
    __tablename__ = "climate_data"
    __table_args__ = (UniqueConstraint("region_id", "date", name="uq_climate_data_region_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    location = mapped_column(
        Geometry(geometry_type="POLYGON", srid=4326, spatial_index=True), nullable=False
    )
    temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    humidity: Mapped[float | None] = mapped_column(Float, nullable=True)
    rainfall: Mapped[float | None] = mapped_column(Float, nullable=True)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    region_id: Mapped[int | None] = mapped_column(
        ForeignKey("regions.id", ondelete="SET NULL"), index=True, nullable=True
    )
