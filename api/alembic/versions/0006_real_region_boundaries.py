"""real region boundaries: 8 bbox seeds -> 24 regions with MultiPolygon geometry

Casts regions.geom from POLYGON to MULTIPOLYGON and upserts all 24 current
Malagasy regions with their real administrative boundaries (bundled GeoJSON, see
app/geo/madagascar.py). Idempotent per code: the original eight codes are updated
in place — their region_id FKs and attached data are untouched — and the sixteen
new regions are inserted.

Revision ID: 0006_real_region_boundaries
Revises: 0005_ingestion_idempotency
Create Date: 2026-07-29
"""
from __future__ import annotations

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.geo.madagascar import REGIONS

revision: str = "0006_real_region_boundaries"
down_revision: str | None = "0005_ingestion_idempotency"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# The eight prototype regions; used only to scope the (lossy) downgrade.
_ORIGINAL_CODES = (
    "ANALAMANGA", "ATSINANANA", "SAVA", "DIANA",
    "BOENY", "MENABE", "ATSIMO_ANDREFANA", "ANOSY",
)


def upgrade() -> None:
    # 1) Widen the geometry column so it can hold real multi-part boundaries.
    op.execute(
        "ALTER TABLE regions ALTER COLUMN geom TYPE geometry(MultiPolygon, 4326) "
        "USING ST_Multi(geom)"
    )

    # 2) Upsert the 24 regions with real geometry. ST_GeomFromGeoJSON builds the
    #    boundary; ST_Multi guarantees MultiPolygon to match the column typmod.
    stmt = sa.text(
        "INSERT INTO regions (code, name, biome, geom) VALUES ("
        ":code, :name, :biome, "
        "ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326))) "
        "ON CONFLICT (code) DO UPDATE SET "
        "name = EXCLUDED.name, biome = EXCLUDED.biome, geom = EXCLUDED.geom"
    )
    for r in REGIONS:
        op.execute(
            stmt.bindparams(
                code=r["code"],
                name=r["name"],
                biome=r["biome"],
                geojson=json.dumps(r["geometry"]),
            )
        )


def downgrade() -> None:
    # Lossy: the new regions are removed and geom is narrowed back to POLYGON by
    # keeping only the largest ring. The original bounding-box seeds are not
    # restored (real boundaries can't be re-derived as envelopes).
    codes = ", ".join(f"'{c}'" for c in _ORIGINAL_CODES)
    op.execute(f"DELETE FROM regions WHERE code NOT IN ({codes})")
    op.execute(
        "ALTER TABLE regions ALTER COLUMN geom TYPE geometry(Polygon, 4326) "
        "USING ST_GeometryN(geom, 1)"
    )
