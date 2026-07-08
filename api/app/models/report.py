"""Reports (class diagram: Report).

`format` is csv|pdf. generate()/export() are service-layer methods (Phase 5).
`user_id`, `params`, and `object_key` are pragmatic additions to persist a
generated report and where its file lives in object storage; flagged as such.
"""
from __future__ import annotations

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Report(Base, TimestampMixin):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    format: Mapped[str] = mapped_column(String(20), nullable=False)  # "csv" | "pdf"
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True
    )
    params: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}", nullable=False)
    object_key: Mapped[str | None] = mapped_column(String(512), nullable=True)

    user = relationship("User")
