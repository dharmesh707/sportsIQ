import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, UploadFile

from app.api.deps import CurrentUser, DbSession
from app.ml_pipeline import run_pipeline
from app.schemas.analysis import AnalysisResult
from app.schemas.common import SportType
from app.services import analysis_store
from app.utils.errors import APIError

router = APIRouter(tags=["analysis"])

_MAX_VIDEO_BYTES = 100 * 1024 * 1024  # 100MB - generous for a phone clip, stops abuse
_ALLOWED_CONTENT_TYPES = {
    "video/mp4", "video/quicktime", "video/x-msvideo", "video/webm", "video/3gpp",
}


@router.post("/analyze", response_model=AnalysisResult)
async def analyze(
    current_user: CurrentUser,
    db: DbSession,
    video: UploadFile | None = File(None),
    sportType: SportType = Form(...),  # noqa: N803 - matches contract's multipart field name exactly
) -> AnalysisResult:
    """
    Routes badminton uploads through the real video detector. Other sports keep
    the existing classifier/mocked pipeline until their implementations land.
    """
    if video is None or not video.filename:
        raise APIError(
            status_code=400,
            code="VALIDATION_ERROR",
            message="Video file is required.",
        )
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

    temp_path: Path | None = None
    try:
        suffix = Path(video.filename or "").suffix.lower() or ".mp4"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
            temp_file.write(video_bytes)
            temp_path = Path(temp_file.name)

        try:
            result = run_pipeline(temp_path, sportType)
        except FileNotFoundError as exc:
            raise APIError(
                status_code=500,
                code="INTERNAL_ERROR",
                message=str(exc),
            ) from exc
        except ValueError as exc:
            status_code = 422 if "Insufficient pose detection" in str(exc) else 400
            raise APIError(
                status_code=status_code,
                code="VIDEO_PROCESSING_FAILED" if status_code == 422 else "VALIDATION_ERROR",
                message=str(exc),
            ) from exc

        analysis_store.save(db, current_user.id, result)
        return result
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


@router.get("/analyze/{analysis_id}", response_model=AnalysisResult)
def get_analysis(current_user: CurrentUser, db: DbSession, analysis_id: str) -> AnalysisResult:
    """
    Contract section 2.4: full AnalysisResult detail for one past analysis.
    Scoped to the current user - an analysis_id belonging to another user
    returns the same 404 as one that doesn't exist, so ownership can't be
    probed by testing for 403 vs 404.
    """
    result = analysis_store.get_by_id(db, current_user.id, analysis_id)
    if result is None:
        raise APIError(
            status_code=404,
            code="NOT_FOUND",
            message="No analysis found with that id.",
        )
    return result
