"""
CONTRACT NOTE: API_CONTRACT.md says GET /dashboard and GET /progress are
"unchanged from v1.0 shape — see existing code." I don't have the old
BadmintonIQ v1.0 backend code in front of me to port the exact shape from,
so DashboardResponse/ProgressResponse below are a reasonable placeholder,
NOT a confirmed match to v1.0.

ACTION NEEDED: when you (Dharmesh) cherry-pick from the old BadmintonIQ repo
per the brief's "Repo strategy" section, replace these two schemas with the
actual v1.0 field names verbatim, then delete this docstring's warning.
Don't let the frontend teammate build against this placeholder for more
than a day without confirming it against the real v1.0 shape.
"""

from datetime import datetime

from .base import CamelModel
from .common import SportType


class RecentAnalysisItem(CamelModel):
    analysis_id: str
    sport_type: SportType
    action_label: str
    overall_score: float
    created_at: datetime


class DashboardResponse(CamelModel):
    total_analyses: int
    average_score: float
    current_streak_days: int
    recent_analyses: list[RecentAnalysisItem]


class ProgressPoint(CamelModel):
    date: datetime
    overall_score: float


class ProgressResponse(CamelModel):
    sport_type: SportType
    points: list[ProgressPoint]
