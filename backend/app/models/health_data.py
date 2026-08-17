"""
Real persistence for health data - replaces health_data.py's in-memory dict.
One row per user (upsert on sync), matching the contract exactly: only a
current /health-data/summary is exposed, no history endpoint exists, so no
history needs to be stored.
"""
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class HealthDataRecord(Base):
    __tablename__ = "health_data"

    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), primary_key=True)
    steps: Mapped[int] = mapped_column(Integer, nullable=False)
    heart_rate_avg: Mapped[float] = mapped_column(Float, nullable=False)
    active_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    last_synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
