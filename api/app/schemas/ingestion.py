from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class IngestionRequest(BaseModel):
    start: date = Field(description="Inclusive start date")
    end: date = Field(description="Inclusive end date")
    region_code: str | None = Field(default=None, description="Limit to one region; omit for all")
    run_async: bool = Field(default=True, description="Queue the job (True) or run inline (False)")


class JobRef(BaseModel):
    job_id: str | None
    status: str
    detail: str
    result: dict | None = None
