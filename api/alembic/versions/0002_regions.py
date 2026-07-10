"""regions table + region_id FKs + Madagascar seed

Revision ID: 0002_regions
Revises: 0001_initial
Create Date: 2026-07-06
"""
from __future__ import annotations

from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from alembic import op

from app.geo.madagascar import REGIONS

revision: str = "0002_regions"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_POLYGON = geoalchemy2.Geometry(geometry_type="POLYGON", srid=4326, spatial_index=False)

_TABLES_WITH_REGION = [
    "satellite_data",
    "climate_data",
    "species_observations",
    "deforestation_events",
]


def upgrade() -> None:
    op.create_table(
        "regions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("biome", sa.String(64), nullable=True),
        sa.Column("geom", _POLYGON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_regions_code", "regions", ["code"], unique=True)
    op.create_index("idx_regions_geom", "regions", ["geom"], postgresql_using="gist")

    for table in _TABLES_WITH_REGION:
        op.add_column(table, sa.Column("region_id", sa.Integer(), nullable=True))
        op.create_foreign_key(
            f"fk_{table}_region_id", table, "regions", ["region_id"], ["id"], ondelete="SET NULL"
        )
        op.create_index(f"ix_{table}_region_id", table, ["region_id"])

    # Seed regions (approx bounding boxes) via ST_MakeEnvelope.
    for r in REGIONS:
        lon_min, lat_min, lon_max, lat_max = r["bbox"]
        op.execute(
            sa.text(
                "INSERT INTO regions (code, name, biome, geom) "
                "VALUES (:code, :name, :biome, "
                "ST_MakeEnvelope(:lon_min, :lat_min, :lon_max, :lat_max, 4326)) "
                "ON CONFLICT (code) DO NOTHING"
            ).bindparams(
                code=r["code"], name=r["name"], biome=r["biome"],
                lon_min=lon_min, lat_min=lat_min, lon_max=lon_max, lat_max=lat_max,
            )
        )


def downgrade() -> None:
    for table in _TABLES_WITH_REGION:
        op.drop_index(f"ix_{table}_region_id", table_name=table)
        op.drop_constraint(f"fk_{table}_region_id", table, type_="foreignkey")
        op.drop_column(table, "region_id")
    op.drop_table("regions")
