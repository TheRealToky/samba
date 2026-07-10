"""prediction_results: add payload JSONB + region_id

Revision ID: 0003_prediction_payload
Revises: 0002_regions
Create Date: 2026-07-06
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_prediction_payload"
down_revision: str | None = "0002_regions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "prediction_results",
        sa.Column("payload", postgresql.JSONB(), nullable=False, server_default="{}"),
    )
    op.add_column("prediction_results", sa.Column("region_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_prediction_results_region_id", "prediction_results", "regions",
        ["region_id"], ["id"], ondelete="SET NULL",
    )
    op.create_index("ix_prediction_results_region_id", "prediction_results", ["region_id"])


def downgrade() -> None:
    op.drop_index("ix_prediction_results_region_id", table_name="prediction_results")
    op.drop_constraint("fk_prediction_results_region_id", "prediction_results", type_="foreignkey")
    op.drop_column("prediction_results", "region_id")
    op.drop_column("prediction_results", "payload")
