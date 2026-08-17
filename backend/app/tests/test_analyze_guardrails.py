"""Tests for /analyze upload guardrails - content-type allowlist, size cap, empty file."""
from app.tests.test_contract_smoke import _register_and_login, client


def test_analyze_rejects_non_video_content_type():
    token = _register_and_login()
    res = client.post(
        "/analyze",
        headers={"Authorization": f"Bearer {token}"},
        files={"video": ("clip.txt", b"not a video", "text/plain")},
        data={"sportType": "badminton"},
    )
    assert res.status_code == 422
    body = res.json()
    assert body["error"]["code"] == "VIDEO_PROCESSING_FAILED"


def test_analyze_rejects_empty_video():
    token = _register_and_login()
    res = client.post(
        "/analyze",
        headers={"Authorization": f"Bearer {token}"},
        files={"video": ("clip.mp4", b"", "video/mp4")},
        data={"sportType": "badminton"},
    )
    assert res.status_code == 400
    body = res.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"


def test_analyze_rejects_oversized_video():
    token = _register_and_login()
    oversized = b"x" * (101 * 1024 * 1024)  # 1MB over the 100MB cap
    res = client.post(
        "/analyze",
        headers={"Authorization": f"Bearer {token}"},
        files={"video": ("clip.mp4", oversized, "video/mp4")},
        data={"sportType": "badminton"},
    )
    assert res.status_code == 400
    body = res.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"


def test_analyze_accepts_allowed_video_types():
    token = _register_and_login()
    for content_type in ["video/mp4", "video/quicktime", "video/webm"]:
        res = client.post(
            "/analyze",
            headers={"Authorization": f"Bearer {token}"},
            files={"video": ("clip.mov", b"real-ish video bytes", content_type)},
            data={"sportType": "badminton"},
        )
        assert res.status_code == 200, f"{content_type} should be accepted"
