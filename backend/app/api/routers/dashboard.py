from fastapi import APIRouter, Query

from app.api.deps import CurrentUser
from app.schemas.common import SportType
from app.schemas.dashboard import (
    DashboardResponse,
    ProgressPoint,
    ProgressResponse,
    RecentAnalysisItem,
)
from app.services import mock_store

router = APIRouter(tags=["analysis"])


@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(current_user: CurrentUser) -> DashboardResponse:
    # See schemas/dashboard.py docstring: shape is a placeholder pending v1.0 port.
    analyses = mock_store.list_for_user(current_user.id)
    avg = round(sum(a.overall_score for a in analyses) / len(analyses), 1) if analyses else 0.0
    return DashboardResponse(
        total_analyses=len(analyses),
        average_score=avg,
        current_streak_days=1 if analyses else 0,
        recent_analyses=[
            RecentAnalysisItem(
                analysis_id=a.analysis_id,
                sport_type=a.sport_type,
                action_label=a.action_label,
                overall_score=a.overall_score,
                created_at=a.created_at,
            )
            for a in analyses[:5]
        ],
    )


@router.get("/progress", response_model=ProgressResponse)
def get_progress(
    current_user: CurrentUser,
    sportType: SportType = Query(...),  # noqa: N803 - contract field naming
) -> ProgressResponse:
    # See schemas/dashboard.py docstring: shape is a placeholder pending v1.0 port.
    analyses = [a for a in mock_store.list_for_user(current_user.id) if a.sport_type == sportType]
    return ProgressResponse(
        sport_type=sportType,
        points=[ProgressPoint(date=a.created_at, overall_score=a.overall_score) for a in analyses],
    )
