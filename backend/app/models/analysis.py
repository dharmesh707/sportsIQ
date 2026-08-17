"""
Real persistence for AnalysisResult - replaces the in-memory mock_store.py.
JSON-typed columns (metrics, joint_angles, strengths, recommendations) mirror
the contract's open-map/list fields exactly rather than flattening them into
rigid columns, matching AnalysisResult's own design intent (contract-first,
sport-agnostic core, no schema fragmentation per sport).
"""
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class AnalysisRecord(Base):
    __tablename__ = "analyses"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), index=True, nullable=False)
    sport_type: Mapped[str] = mapped_column(String, nullable=False)
    action_label: Mapped[str] = mapped_column(String, nullable=False)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    professional_comparison: Mapped[str] = mapped_column(String, nullable=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    joint_angles: Mapped[dict[str, float]] = mapped_column(JSON, nullable=False, default=dict)
    strengths: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    recommendations: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )

    faults: Mapped[list["FaultRecord"]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )


class FaultRecord(Base):
    __tablename__ = "faults"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    analysis_id: Mapped[str] = mapped_column(
        String, ForeignKey("analyses.id"), index=True, nullable=False
    )
    fault_code: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)  # "hard" | "soft"
    description: Mapped[str] = mapped_column(String, nullable=False)
    frame: Mapped[int] = mapped_column(Integer, nullable=False)
    reference_source: Mapped[str | None] = mapped_column(String, nullable=True)

    analysis: Mapped["AnalysisRecord"] = relationship(back_populates="faults")
