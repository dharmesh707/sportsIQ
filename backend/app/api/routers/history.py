import math

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbSession
from app.schemas.analysis import AnalysisResultSummary, HistoryResponse, Pagination
from app.schemas.common import SportType
from app.services import analysis_store

router = APIRouter(tags=["analysis"])


@router.get("/history", response_model=HistoryResponse)
def get_history(
    current_user: CurrentUser,
    db: DbSession,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),  # noqa: N803
    sportType: SportType | None = Query(None),  # noqa: N803
) -> HistoryResponse:
    analyses = analysis_store.list_for_user(db, current_user.id)  # newest-first
    if sportType is not None:
        analyses = [a for a in analyses if a.sport_type == sportType]

    total_items = len(analyses)
    total_pages = math.ceil(total_items / pageSize) if total_items else 0
    start = (page - 1) * pageSize
    page_items = analyses[start : start + pageSize]

    summaries = []
    for a in page_items:
        hard = sum(1 for f in a.faults if f.type.value == "hard")
        soft = sum(1 for f in a.faults if f.type.value == "soft")
        summaries.append(
            AnalysisResultSummary(
                analysis_id=a.analysis_id,
                sport_type=a.sport_type,
                action_label=a.action_label,
                overall_score=a.overall_score,
                hard_fault_count=hard,
                soft_fault_count=soft,
                created_at=a.created_at,
            )
        )

    return HistoryResponse(
        analyses=summaries,
        pagination=Pagination(
            page=page,
            page_size=pageSize,
            total_items=total_items,
            total_pages=total_pages,
        ),
    )
