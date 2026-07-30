"""Region entity (pragmatic addition, not in the class diagram).

Anchors satellite/climate/observation data to a place so datasets can be
spatial-temporally aligned and queried cheaply by an indexed FK, while the
geometry still supports true spatial queries (NFR-2).
"""
from __future__ import annotations

from geoalchemy2 import Geometry
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Region(Base, TimestampMixin):
    __tablename__ = "regions"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    biome: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # MultiPolygon: real administrative boundaries (islands, complex coastlines);
    # see app/geo/madagascar.py. Was POLYGON in the bounding-box prototype.
    geom = mapped_column(
        Geometry(geometry_type="MULTIPOLYGON", srid=4326, spatial_index=True), nullable=False
    )
