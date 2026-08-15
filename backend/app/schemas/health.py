from datetime import datetime

from .base import CamelModel


class HealthDataSyncRequest(CamelModel):
    steps: int
    heart_rate_avg: float
    active_minutes: int
    synced_at: datetime


class OkResponse(CamelModel):
    ok: bool = True


class HealthDataSummary(CamelModel):
    steps: int
    heart_rate_avg: float
    active_minutes: int
    last_synced_at: datetime | None = None
