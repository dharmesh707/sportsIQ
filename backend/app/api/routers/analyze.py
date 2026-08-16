from fastapi import APIRouter, File, Form, UploadFile

from app.api.deps import CurrentUser
from app.ml_pipeline import run_pipeline
from app.schemas.analysis import AnalysisResult
from app.schemas.common import SportType
from app.services import mock_store

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
