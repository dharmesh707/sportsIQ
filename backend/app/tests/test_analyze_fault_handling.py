"""
Fault taxonomy for POST /analyze.

Two things are asserted everywhere: the correct HTTP status + contract error
code, and that no internal detail (stack trace, module path, exception class)
reaches the response body. The second matters as much as the first - a
MediaPipe traceback rendered in a mobile error banner is both useless to the
user and an information leak.
"""

import importlib
from pathlib import Path

from app.schemas.common import SportType
from app.tests.test_contract_smoke import _register_and_login, client
from scripts.analyze_badminton_video_rule_based import (
    InsufficientPoseError,
    VideoError,
)

router_module = importlib.import_module("app.api.routers.analyze")

_LEAK_MARKERS = ("Traceback", "File \"", "mediapipe", "app/services", "site-packages")


def _post(token: str, sport: str = "badminton"):
    return client.post(
        "/analyze",
        headers={"Authorization": f"Bearer {token}"},
        files={"video": ("clip.mp4", b"video bytes", "video/mp4")},
        data={"sportType": sport},
    )


def _assert_contract_error(response, status: int, code: str):
    assert response.status_code == status
    body = response.json()
    assert set(body.keys()) == {"error"}
    assert set(body["error"].keys()) == {"code", "message"}
    assert body["error"]["code"] == code
    message = body["error"]["message"]
    assert message
    for marker in _LEAK_MARKERS:
        assert marker not in message, f"internal detail leaked to user: {marker!r}"
    return body


# --------------------------------------------------------------------------
# Upload-level validation (pre-inference)
# --------------------------------------------------------------------------


def test_missing_video_returns_400():
    token = _register_and_login()
    response = client.post(
        "/analyze",
        headers={"Authorization": f"Bearer {token}"},
        data={"sportType": "badminton"},
    )
    _assert_contract_error(response, 400, "VALIDATION_ERROR")


def test_empty_video_returns_400():
    token = _register_and_login()
    response = client.post(
        "/analyze",
        headers={"Authorization": f"Bearer {token}"},
        files={"video": ("clip.mp4", b"", "video/mp4")},
        data={"sportType": "badminton"},
    )
    _assert_contract_error(response, 400, "VALIDATION_ERROR")


def test_unsupported_content_type_returns_422():
    token = _register_and_login()
    response = client.post(
        "/analyze",
        headers={"Authorization": f"Bearer {token}"},
        files={"video": ("notes.pdf", b"%PDF-1.4", "application/pdf")},
        data={"sportType": "badminton"},
    )
    _assert_contract_error(response, 422, "VIDEO_PROCESSING_FAILED")


# --------------------------------------------------------------------------
# Inference-level failures
# --------------------------------------------------------------------------


def test_insufficient_pose_returns_422_with_actionable_message(monkeypatch):
    def boom(video_path, sport_type):
        raise InsufficientPoseError("Insufficient pose detection: 3 of 90 (3.3%)")

    monkeypatch.setattr(router_module, "run_pipeline", boom)
    body = _assert_contract_error(_post(_register_and_login()), 422, "VIDEO_PROCESSING_FAILED")
    message = body["error"]["message"].lower()
    # Must tell the user what to actually DO, not just that it failed.
    assert "full body" in message or "lighting" in message


def test_unreadable_video_returns_422(monkeypatch):
    def boom(video_path, sport_type):
        raise VideoError("This video could not be decoded. Try re-exporting it as an MP4.")

    monkeypatch.setattr(router_module, "run_pipeline", boom)
    _assert_contract_error(_post(_register_and_login()), 422, "VIDEO_PROCESSING_FAILED")


def test_missing_model_returns_500_without_exposing_paths(monkeypatch):
    def boom(video_path, sport_type):
        raise FileNotFoundError(
            "MediaPipe pose model not found at /srv/app/models/pose_landmarker_full.task"
        )

    monkeypatch.setattr(router_module, "run_pipeline", boom)
    body = _assert_contract_error(_post(_register_and_login()), 500, "INTERNAL_ERROR")
    assert "pose_landmarker_full.task" not in body["error"]["message"]
    assert "/srv/app" not in body["error"]["message"]


def test_missing_dependency_returns_500(monkeypatch):
    def boom(video_path, sport_type):
        raise ImportError("No module named 'mediapipe'")

    monkeypatch.setattr(router_module, "run_pipeline", boom)
    body = _assert_contract_error(_post(_register_and_login()), 500, "INTERNAL_ERROR")
    assert "mediapipe" not in body["error"]["message"]


def test_unexpected_inference_failure_returns_500(monkeypatch):
    def boom(video_path, sport_type):
        raise RuntimeError("CUDA kernel exploded at 0xdeadbeef")

    monkeypatch.setattr(router_module, "run_pipeline", boom)
    body = _assert_contract_error(_post(_register_and_login()), 500, "INTERNAL_ERROR")
    assert "0xdeadbeef" not in body["error"]["message"]


def test_legacy_bare_valueerror_still_maps_to_422(monkeypatch):
    """Backward compatibility: v1 signalled this with a plain ValueError."""
    def boom(video_path, sport_type):
        raise ValueError("Insufficient pose detection: 2 detected frames out of 80 (2.5%)")

    monkeypatch.setattr(router_module, "run_pipeline", boom)
    _assert_contract_error(_post(_register_and_login()), 422, "VIDEO_PROCESSING_FAILED")


# --------------------------------------------------------------------------
# Temporary file cleanup
# --------------------------------------------------------------------------


def test_temp_file_is_deleted_after_inference_failure(monkeypatch):
    """
    The failure path is the one that leaks. A `finally` that only runs on
    success would fill the disk with uploaded video over time.
    """
    seen: dict[str, Path] = {}

    def boom(video_path, sport_type):
        seen["path"] = video_path
        assert video_path.exists()
        raise RuntimeError("inference blew up")

    monkeypatch.setattr(router_module, "run_pipeline", boom)
    _post(_register_and_login())
    assert not seen["path"].exists()


def test_temp_file_is_deleted_after_pose_rejection(monkeypatch):
    seen: dict[str, Path] = {}

    def boom(video_path, sport_type):
        seen["path"] = video_path
        raise InsufficientPoseError("Insufficient pose detection: 1 of 60")

    monkeypatch.setattr(router_module, "run_pipeline", boom)
    _post(_register_and_login())
    assert not seen["path"].exists()


# --------------------------------------------------------------------------
# Sports registry endpoint
# --------------------------------------------------------------------------


def test_sports_endpoint_lists_support_status():
    response = client.get("/sports")
    assert response.status_code == 200
    sports = response.json()["sports"]
    assert len(sports) == len(SportType)
    badminton = next(s for s in sports if s["sportType"] == "badminton")
    assert badminton["status"] == "SUPPORTED"
    assert badminton["dataSource"] == "measured"
    assert sports[0]["sportType"] == "badminton"  # supported sorts first


def test_preview_sport_response_is_labelled_simulated():
    token = _register_and_login()
    response = _post(token, sport="tennis")
    assert response.status_code == 200
    body = response.json()
    assert body["dataSource"] == "simulated"
    assert "PREVIEW ONLY" in body["professionalComparison"]
