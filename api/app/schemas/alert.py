from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AlertRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    alert_type: str
    severity: str
    message: str
    acknowledged: bool
    notified: bool
    region_id: int | None = None
    prediction_id: int | None = None
    created_at: datetime
