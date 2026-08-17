from fastapi import APIRouter, File, Form, UploadFile

from app.api.deps import CurrentUser
from app.ml_pipeline import run_pipeline
from app.schemas.analysis import AnalysisResult
from app.schemas.common import SportType
from app.services import mock_store
from app.utils.errors import APIError

router = APIRouter(tags=["analysis"])

_MAX_VIDEO_BYTES = 100 * 1024 * 1024  # 100MB - generous for a phone clip, stops abuse
_ALLOWED_CONTENT_TYPES = {
    "video/mp4", "video/quicktime", "video/x-msvideo", "video/webm", "video/3gpp",
}


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

    Guardrails added: content-type allowlist (rejects non-video uploads
    before they reach the pipeline) and a 100MB size cap (rejects after
    reading, since UploadFile doesn't expose size upfront without reading -
    still bounded, just not zero-cost for a huge rejected file).
    """
    if video.content_type not in _ALLOWED_CONTENT_TYPES:
        raise APIError(
            status_code=422,
            code="VIDEO_PROCESSING_FAILED",
            message=(
                f"Unsupported video type '{video.content_type}'. "
                f"Accepted types: {', '.join(sorted(_ALLOWED_CONTENT_TYPES))}."
            ),
        )

    video_bytes = await video.read()

    if len(video_bytes) > _MAX_VIDEO_BYTES:
        raise APIError(
            status_code=400,
            code="VALIDATION_ERROR",
            message=f"Video exceeds the {_MAX_VIDEO_BYTES // (1024 * 1024)}MB size limit.",
        )
    if len(video_bytes) == 0:
        raise APIError(
            status_code=400,
            code="VALIDATION_ERROR",
            message="Uploaded video file is empty.",
        )

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
        code="NOT_FOUND",
        message="No analysis found with that id.",
    )
