"""environmental_alerts: add alert_type, notified, region_id

Revision ID: 0004_alert_fields
Revises: 0003_prediction_payload
Create Date: 2026-07-06
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_alert_fields"
down_revision: str | None = "0003_prediction_payload"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("environmental_alerts", sa.Column("alert_type", sa.String(50), nullable=False, server_default="deforestation"))
    op.add_column("environmental_alerts", sa.Column("notified", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("environmental_alerts", sa.Column("region_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_environmental_alerts_region_id", "environmental_alerts", "regions",
        ["region_id"], ["id"], ondelete="SET NULL",
    )
    op.create_index("ix_environmental_alerts_region_id", "environmental_alerts", ["region_id"])


def downgrade() -> None:
    op.drop_index("ix_environmental_alerts_region_id", table_name="environmental_alerts")
    op.drop_constraint("fk_environmental_alerts_region_id", "environmental_alerts", type_="foreignkey")
    op.drop_column("environmental_alerts", "region_id")
    op.drop_column("environmental_alerts", "notified")
    op.drop_column("environmental_alerts", "alert_type")
