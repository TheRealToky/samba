"""initial schema: enable PostGIS + create all core tables

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-06
"""
from __future__ import annotations

from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Geometry columns are declared with spatial_index=False here; GiST indexes are
# created explicitly below so their names/type are fully under our control.
_POLYGON = geoalchemy2.Geometry(geometry_type="POLYGON", srid=4326, spatial_index=False)
_POINT = geoalchemy2.Geometry(geometry_type="POINT", srid=4326, spatial_index=False)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=False, server_default="student_public"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # --- species ---
    op.create_table(
        "species",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("scientific_name", sa.String(255), nullable=False),
        sa.Column("conservation_status", sa.String(100), nullable=True),
        sa.Column("endemic", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_species_scientific_name", "species", ["scientific_name"], unique=True)

    # --- ml_models ---
    op.create_table(
        "ml_models",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("hyperparameters", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_ml_models_name", "ml_models", ["name"])

    # --- satellite_data ---
    op.create_table(
        "satellite_data",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("location", _POLYGON, nullable=False),
        sa.Column("ndvi", sa.Float(), nullable=False),
        sa.Column("date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_satellite_data_date", "satellite_data", ["date"])
    op.create_index("idx_satellite_data_location", "satellite_data", ["location"], postgresql_using="gist")

    # --- climate_data ---
    op.create_table(
        "climate_data",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("location", _POLYGON, nullable=False),
        sa.Column("temperature", sa.Float(), nullable=True),
        sa.Column("humidity", sa.Float(), nullable=True),
        sa.Column("rainfall", sa.Float(), nullable=True),
        sa.Column("date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_climate_data_date", "climate_data", ["date"])
    op.create_index("idx_climate_data_location", "climate_data", ["location"], postgresql_using="gist")

    # --- species_observations ---
    op.create_table(
        "species_observations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("species_id", sa.Integer(), sa.ForeignKey("species.id", ondelete="CASCADE"), nullable=False),
        sa.Column("location", _POINT, nullable=False),
        sa.Column("date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_species_observations_species_id", "species_observations", ["species_id"])
    op.create_index("ix_species_observations_date", "species_observations", ["date"])
    op.create_index(
        "idx_species_observations_location", "species_observations", ["location"], postgresql_using="gist"
    )

    # --- prediction_results ---
    op.create_table(
        "prediction_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("type", sa.String(100), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ml_model_id", sa.Integer(), sa.ForeignKey("ml_models.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_prediction_results_date", "prediction_results", ["date"])
    op.create_index("ix_prediction_results_ml_model_id", "prediction_results", ["ml_model_id"])

    # --- deforestation_events ---
    op.create_table(
        "deforestation_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("location", _POLYGON, nullable=False),
        sa.Column("vegetation_loss", sa.Float(), nullable=False),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ml_model_id", sa.Integer(), sa.ForeignKey("ml_models.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_deforestation_events_start_date", "deforestation_events", ["start_date"])
    op.create_index("ix_deforestation_events_end_date", "deforestation_events", ["end_date"])
    op.create_index("ix_deforestation_events_ml_model_id", "deforestation_events", ["ml_model_id"])
    op.create_index(
        "idx_deforestation_events_location", "deforestation_events", ["location"], postgresql_using="gist"
    )

    # --- environmental_alerts ---
    op.create_table(
        "environmental_alerts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("severity", sa.String(50), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("acknowledged", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "prediction_id",
            sa.Integer(),
            sa.ForeignKey("prediction_results.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_environmental_alerts_prediction_id", "environmental_alerts", ["prediction_id"])

    # --- reports ---
    op.create_table(
        "reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("format", sa.String(20), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("params", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("object_key", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_reports_user_id", "reports", ["user_id"])


def downgrade() -> None:
    op.drop_table("reports")
    op.drop_table("environmental_alerts")
    op.drop_table("deforestation_events")
    op.drop_table("prediction_results")
    op.drop_table("species_observations")
    op.drop_table("climate_data")
    op.drop_table("satellite_data")
    op.drop_table("ml_models")
    op.drop_table("species")
    op.drop_table("users")
    # PostGIS extension is left installed intentionally.
