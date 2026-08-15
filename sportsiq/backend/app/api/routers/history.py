from fastapi import APIRouter

from app.api.deps import CurrentUser
from app.schemas.analysis import AnalysisResultSummary, HistoryResponse
from app.services import mock_store

router = APIRouter(tags=["analysis"])


@router.get("/history", response_model=HistoryResponse)
def get_history(current_user: CurrentUser) -> HistoryResponse:
    analyses = mock_store.list_for_user(current_user.id)
    summaries = [
        AnalysisResultSummary(
            analysis_id=a.analysis_id,
            sport_type=a.sport_type,
            action_label=a.action_label,
            overall_score=a.overall_score,
            created_at=a.created_at,
        )
        for a in analyses
    ]
    return HistoryResponse(analyses=summaries)
