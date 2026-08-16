from fastapi import APIRouter, File, Form, UploadFile

from app.api.deps import CurrentUser
from app.ml_pipeline import run_pipeline
from app.schemas.analysis import AnalysisResult
from app.schemas.common import SportType
from app.services import mock_store
from app.utils.errors import APIError

router = APIRouter(tags=["analysis"])


@router.post("/analyze", response_model=AnalysisResult)
async def analyze(
    current_user: CurrentUser,
    video: UploadFile = File(...),
    sportType: SportType = Form(...),  # noqa: N803 - matches contract's multipart field name exactly
) -> AnalysisResult:
    """
    Routes to app/ml_pipeline.py's run_pipeline(), which auto-detects whether
    a real per-sport classifier exists yet (ml/sports/<sport>/classifier.py)
    and falls back to mock data if not. This router does not need to change
    when real ML lands - see ml_pipeline.py's docstring for the plug-in
    contract.
    """
    video_bytes = await video.read()
    result = run_pipeline(video_bytes, sportType)
    mock_store.save(current_user.id, result)
    return result


@router.get("/analyze/{analysis_id}", response_model=AnalysisResult)
def get_analysis(current_user: CurrentUser, analysis_id: str) -> AnalysisResult:
    """
    Contract section 2.4: full AnalysisResult detail for one past analysis,
    referenced from GET /history's trimmed summary items. Scoped to the
    current user - an analysis_id that exists but belongs to someone else
    returns the same 404 as one that doesn't exist at all, so this can't be
    used to enumerate other users' analysis IDs.
    """
    for result in mock_store.list_for_user(current_user.id):
        if result.analysis_id == analysis_id:
            return result
    raise APIError(
        status_code=404,
        code="analysis_not_found",
        message="No analysis found with that id.",
    )
