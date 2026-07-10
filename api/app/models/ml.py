"""ML entities (class diagram: MLModel, PredictionResult, DeforestationEvent).

MLModel produces PredictionResult and DeforestationEvent. train()/predict() live
in the service/ML layer (Phase 3); this module is the persistence shape.
"""
from __future__ import annotations

from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class MLModel(Base, TimestampMixin):
    __tablename__ = "ml_models"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    hyperparameters: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}", nullable=False)

    predictions: Mapped[list["PredictionResult"]] = relationship(back_populates="ml_model")
    deforestation_events: Mapped[list["DeforestationEvent"]] = relationship(back_populates="ml_model")


class PredictionResult(Base, TimestampMixin):
    __tablename__ = "prediction_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. "deforestation", "sdm"
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    # Addition: carries the actual prediction output (forecast points, loss, etc.).
    payload: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}", nullable=False)
    region_id: Mapped[int | None] = mapped_column(
        ForeignKey("regions.id", ondelete="SET NULL"), index=True, nullable=True
    )
    ml_model_id: Mapped[int | None] = mapped_column(
        ForeignKey("ml_models.id", ondelete="SET NULL"), index=True, nullable=True
    )

    ml_model: Mapped["MLModel | None"] = relationship(back_populates="predictions")
    alerts: Mapped[list["EnvironmentalAlert"]] = relationship(back_populates="prediction")


class DeforestationEvent(Base, TimestampMixin):
    __tablename__ = "deforestation_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    location = mapped_column(
        Geometry(geometry_type="POLYGON", srid=4326, spatial_index=True), nullable=False
    )
    vegetation_loss: Mapped[float] = mapped_column(Float, nullable=False)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    ml_model_id: Mapped[int | None] = mapped_column(
        ForeignKey("ml_models.id", ondelete="SET NULL"), index=True, nullable=True
    )
    region_id: Mapped[int | None] = mapped_column(
        ForeignKey("regions.id", ondelete="SET NULL"), index=True, nullable=True
    )

    ml_model: Mapped["MLModel | None"] = relationship(back_populates="deforestation_events")


# Imported at bottom to avoid a circular import at module load time.
from app.models.alert import EnvironmentalAlert  # noqa: E402,F401
