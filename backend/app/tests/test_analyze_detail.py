"""Tests for GET /analyze/{analysisId} - contract section 2.4."""
from app.tests.test_contract_smoke import _register_and_login, client


def test_get_analysis_returns_full_shape():
    token = _register_and_login()
    create_res = client.post(
        "/analyze",
        headers={"Authorization": f"Bearer {token}"},
        files={"video": ("clip.mp4", b"fake", "video/mp4")},
        data={"sportType": "badminton"},
    )
    analysis_id = create_res.json()["analysisId"]

    res = client.get(
        f"/analyze/{analysis_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["analysisId"] == analysis_id
    assert set(body.keys()) == {
        "analysisId", "sportType", "actionLabel", "overallScore",
        "professionalComparison", "metrics", "jointAngles", "faults",
        "strengths", "recommendations", "createdAt",
    }


def test_get_analysis_unknown_id_returns_404_contract_shape():
    token = _register_and_login()
    res = client.get(
        "/analyze/does-not-exist",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 404
    assert set(res.json().keys()) == {"error"}
    assert set(res.json()["error"].keys()) == {"code", "message"}


def test_get_analysis_requires_auth():
    res = client.get("/analyze/some-id")
    assert res.status_code == 401


def test_get_analysis_scoped_to_owner_not_other_users():
    token_a = _register_and_login()
    token_b = _register_and_login()

    create_res = client.post(
        "/analyze",
        headers={"Authorization": f"Bearer {token_a}"},
        files={"video": ("clip.mp4", b"fake", "video/mp4")},
        data={"sportType": "badminton"},
    )
    analysis_id = create_res.json()["analysisId"]

    # user B tries to fetch user A's analysis - must 404, not 403,
    # so existence of the id isn't leaked either
    res = client.get(
        f"/analyze/{analysis_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res.status_code == 404
