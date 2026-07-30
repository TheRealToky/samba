"""ingestion idempotency: species_observations.external_id + unique constraints

Lets ingestion upsert instead of duplicating rows when a date window is
re-ingested (required before live / scheduled ingestion). Existing duplicate
rows are collapsed (keeping the lowest id) before the constraints are added so
the migration is safe to apply to a populated dev database.

Revision ID: 0005_ingestion_idempotency
Revises: 0004_alert_fields
Create Date: 2026-07-10
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_ingestion_idempotency"
down_revision: str | None = "0004_alert_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("species_observations", sa.Column("external_id", sa.String(128), nullable=True))

    # Collapse pre-existing duplicates (keep lowest id). region_id = region_id
    # skips NULL region rows, matching the constraint (NULLs stay distinct).
    op.execute(
        "DELETE FROM satellite_data a USING satellite_data b "
        "WHERE a.id > b.id AND a.region_id = b.region_id AND a.date = b.date"
    )
    op.execute(
        "DELETE FROM climate_data a USING climate_data b "
        "WHERE a.id > b.id AND a.region_id = b.region_id AND a.date = b.date"
    )
    op.execute(
        "DELETE FROM species_observations a USING species_observations b "
        "WHERE a.id > b.id AND a.source = b.source "
        "AND a.external_id = b.external_id AND a.external_id IS NOT NULL"
    )

    op.create_unique_constraint(
        "uq_satellite_data_region_date", "satellite_data", ["region_id", "date"]
    )
    op.create_unique_constraint(
        "uq_climate_data_region_date", "climate_data", ["region_id", "date"]
    )
    op.create_unique_constraint(
        "uq_species_obs_source_external", "species_observations", ["source", "external_id"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_species_obs_source_external", "species_observations", type_="unique")
    op.drop_constraint("uq_climate_data_region_date", "climate_data", type_="unique")
    op.drop_constraint("uq_satellite_data_region_date", "satellite_data", type_="unique")
    op.drop_column("species_observations", "external_id")
