from datetime import datetime

from pydantic import Field

from .base import CamelModel


class HealthDataSyncRequest(CamelModel):
    steps: int = Field(ge=0, le=100_000)
    heart_rate_avg: float = Field(ge=0, le=250)
    active_minutes: int = Field(ge=0, le=1_440)  # can't exceed minutes in a day
    synced_at: datetime


class OkResponse(CamelModel):
    ok: bool = True


class HealthDataSummary(CamelModel):
    steps: int
    heart_rate_avg: float
    active_minutes: int
    last_synced_at: datetime | None = None
