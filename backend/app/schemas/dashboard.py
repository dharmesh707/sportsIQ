from datetime import date, datetime
from typing import Literal, Optional

from .base import CamelModel
from .common import SportType

TrendLabel = Literal["improving", "stable", "declining", "insufficient_data"]
FaultType = Literal["hard", "soft"]


class SportBreakdown(CamelModel):
    sport_type: SportType
    session_count: int
    average_score: float
    last_session_at: Optional[datetime]
    trend: TrendLabel


class RecentSession(CamelModel):
    session_id: str
    sport_type: SportType
    score: float
    hard_fault_count: int
    soft_fault_count: int
    created_at: datetime


class TopFault(CamelModel):
    fault_code: str
    sport_type: SportType
    fault_type: FaultType
    occurrence_count: int


class DashboardSummary(CamelModel):
    total_sessions: int
    sports_practiced: list[SportType]
    current_streak_days: int
    last_session_at: Optional[datetime]


class DashboardResponse(CamelModel):
    summary: DashboardSummary
    sport_breakdown: list[SportBreakdown]
    recent_sessions: list[RecentSession]
    top_faults: list[TopFault]
    recommendations: list[str]


class ProgressRange(CamelModel):
    start: date
    end: date


class ProgressBaseline(CamelModel):
    initial_score: float
    current_score: float
    percent_change: float
    established_at: date


class ProgressDataPoint(CamelModel):
    date: date
    session_id: str
    score: float
    hard_fault_count: int
    soft_fault_count: int


class FaultOccurrence(CamelModel):
    date: date
    count: int


class FaultTrend(CamelModel):
    fault_code: str
    fault_type: FaultType
    occurrences: list[FaultOccurrence]


class ProgressResponse(CamelModel):
    sport_type: SportType
    range: ProgressRange
    baseline: ProgressBaseline
    data_points: list[ProgressDataPoint]
    fault_trends: list[FaultTrend]
