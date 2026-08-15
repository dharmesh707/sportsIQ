from fastapi import APIRouter, File, Form, UploadFile

from app.api.deps import CurrentUser
from app.schemas.analysis import AnalysisResult
from app.schemas.common import SportType
from app.services import mock_store
from app.services.mock_data import build_mock_analysis

router = APIRouter(tags=["analysis"])


@router.post("/analyze", response_model=AnalysisResult)
async def analyze(
    current_user: CurrentUser,
    video: UploadFile = File(...),
    sportType: SportType = Form(...),  # noqa: N803 - matches contract's multipart field name exactly
) -> AnalysisResult:
    """
    DAY 1 STUB: does not touch the uploaded video or run any ML. Just proves
    the multipart contract (video file + sportType form field) works and
    returns a hardcoded-but-correctly-shaped AnalysisResult so the frontend
    can build the Analyze screen today.

    Day 2/3 TODO: replace the body below with a call into
    ml/pose -> ml/angles -> ml/sports/<sport>/ pipeline. Keep reading the
    UploadFile stream (video.file / await video.read()) instead of loading
    the whole thing into memory once real videos start arriving.
    """
    # Touch the file object so multipart parsing is actually exercised end
    # to end (catches "frontend sent the wrong field name" bugs early)
    # without holding the bytes in memory.
    _ = video.filename

    result = build_mock_analysis(sportType)
    mock_store.save(current_user.id, result)
    return result
