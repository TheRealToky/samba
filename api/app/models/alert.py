"""Environmental alerts (class diagram: EnvironmentalAlert).

A PredictionResult can trigger one or more alerts. notify() is a service-layer
method (Phase 4). `acknowledged` is an addition (not in the diagram) to support
the dashboard alert feed; flagged here for transparency.
"""
from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class EnvironmentalAlert(Base, TimestampMixin):
    __tablename__ = "environmental_alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    alert_type: Mapped[str] = mapped_column(String(50), default="deforestation", server_default="deforestation", nullable=False)  # deforestation | biodiversity
    severity: Mapped[str] = mapped_column(String(50), nullable=False)  # low | medium | high | critical
    message: Mapped[str] = mapped_column(Text, nullable=False)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    notified: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    region_id: Mapped[int | None] = mapped_column(
        ForeignKey("regions.id", ondelete="SET NULL"), index=True, nullable=True
    )
    prediction_id: Mapped[int | None] = mapped_column(
        ForeignKey("prediction_results.id", ondelete="SET NULL"), index=True, nullable=True
    )

    prediction: Mapped["PredictionResult | None"] = relationship(back_populates="alerts")


from app.models.ml import PredictionResult  # noqa: E402,F401
