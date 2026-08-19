"""Focused endpoint tests for the real badminton detector integration."""

import importlib
import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.analysis import AnalysisResult
from app.schemas.common import SportType
from app.tests.test_contract_smoke import _register_and_login, client

router_module = importlib.import_module("app.api.routers.analyze")


def _result() -> AnalysisResult:
    return AnalysisResult(
        analysis_id=f"analysis-{uuid.uuid4()}",
        sport_type=SportType.BADMINTON,
        action_label="FH_DRIVE",
        overall_score=42.3,
        professional_comparison="Coarse biomechanics feedback.",
        metrics={"detectedFrames": 15, "detectionRate": 1.0, "contactFrame": 8},
        joint_angles={
            "elbow_angle": 164.9,
            "shoulder_elevation": 21.2,
            "knee_angle": 177.2,
            "hip_shoulder_separation": 6.9,
            "torso_inclination": 17.9,
        },
        faults=[],
        strengths=[],
        recommendations=[],
        created_at=datetime.now(timezone.utc),
    )


def test_badminton_success_uses_temp_path_and_deletes_it(monkeypatch):
    token = _register_and_login()
    seen = {}

    def fake_pipeline(video_path, sport_type):
        seen["path"] = video_path
        seen["sport"] = sport_type
        assert video_path.exists()
        return _result()

    monkeypatch.setattr(router_module, "run_pipeline", fake_pipeline)
    response = client.post(
        "/analyze",
        headers={"Authorization": f"Bearer {token}"},
        files={"video": ("clip.MP4", b"video bytes", "video/mp4")},
        data={"sportType": "badminton"},
    )
    assert response.status_code == 200
    assert seen["sport"] == SportType.BADMINTON
    assert seen["path"].suffix == ".mp4"
    assert not seen["path"].exists()
    body = response.json()
    assert set(body) == {
        "analysisId", "sportType", "actionLabel", "overallScore",
        "professionalComparison", "metrics", "jointAngles", "faults",
        "strengths", "recommendations", "createdAt",
    }
    assert body["sportType"] == "badminton"
    assert body["actionLabel"] == "FH_DRIVE"
    assert body["metrics"]["detectedFrames"] == 15
    assert len(body["jointAngles"]) == 5
    assert all(isinstance(value, (int, float)) for value in body["jointAngles"].values())


def test_badminton_missing_upload_is_400():
    token = _register_and_login()
    response = client.post(
        "/analyze",
        headers={"Authorization": f"Bearer {token}"},
        data={"sportType": "badminton"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_badminton_invalid_sport_type_is_422():
    token = _register_and_login()
    response = client.post(
        "/analyze",
        headers={"Authorization": f"Bearer {token}"},
        files={"video": ("clip.mp4", b"video bytes", "video/mp4")},
        data={"sportType": "not-a-sport"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_badminton_invalid_video_is_400(monkeypatch):
    token = _register_and_login()
    seen = {}

    def fail(video_path, *_):
        seen["path"] = video_path
        raise ValueError("Could not open video: clip.mp4")

    monkeypatch.setattr(router_module, "run_pipeline", fail)
    response = client.post(
        "/analyze",
        headers={"Authorization": f"Bearer {token}"},
        files={"video": ("clip.mp4", b"not video", "video/mp4")},
        data={"sportType": "badminton"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert not seen["path"].exists()


def test_badminton_insufficient_pose_is_422(monkeypatch):
    token = _register_and_login()
    seen = {}

    def fail(video_path, *_):
        seen["path"] = video_path
        raise ValueError("Insufficient pose detection: 2 detected frames")

    monkeypatch.setattr(router_module, "run_pipeline", fail)
    response = client.post(
        "/analyze",
        headers={"Authorization": f"Bearer {token}"},
        files={"video": ("clip.mp4", b"video bytes", "video/mp4")},
        data={"sportType": "badminton"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VIDEO_PROCESSING_FAILED"
    assert not seen["path"].exists()


def test_badminton_missing_model_is_500(monkeypatch):
    token = _register_and_login()
    seen = {}

    def fail(video_path, *_):
        seen["path"] = video_path
        raise FileNotFoundError("MediaPipe model not found: models/pose_landmarker_full.task")

    monkeypatch.setattr(router_module, "run_pipeline", fail)
    response = client.post(
        "/analyze",
        headers={"Authorization": f"Bearer {token}"},
        files={"video": ("clip.mp4", b"video bytes", "video/mp4")},
        data={"sportType": "badminton"},
    )
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert not seen["path"].exists()


def test_badminton_detector_exception_is_500_and_cleans_up(monkeypatch):
    token = _register_and_login()
    seen = {}

    def fail(video_path, *_):
        seen["path"] = video_path
        raise RuntimeError("detector runtime failure")

    monkeypatch.setattr(router_module, "run_pipeline", fail)
    response = TestClient(app, raise_server_exceptions=False).post(
        "/analyze",
        headers={"Authorization": f"Bearer {token}"},
        files={"video": ("clip.mp4", b"video bytes", "video/mp4")},
        data={"sportType": "badminton"},
    )
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert not seen["path"].exists()