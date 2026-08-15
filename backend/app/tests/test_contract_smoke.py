"""
Run with: pytest app/tests/test_contract_smoke.py -v

This isn't a full test suite — it's a fast contract-drift tripwire. Run it
after ANY endpoint change, before you push, per API_CONTRACT.md's rule:
"Integration testing happens daily, not at the end." Every assertion here
maps directly to a rule in the contract file.
"""

import uuid

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _register_and_login() -> str:
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    res = client.post("/auth/register", json={"email": email, "password": "testpass123"})
    assert res.status_code == 201
    return res.json()["accessToken"]


def test_register_response_is_camel_case():
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    res = client.post("/auth/register", json={"email": email, "password": "testpass123"})
    body = res.json()
    # contract: accessToken + user{id, email, createdAt}, camelCase throughout
    assert "accessToken" in body
    assert set(body["user"].keys()) == {"id", "email", "createdAt"}
    assert "access_token" not in body  # snake_case must NOT leak through


def test_duplicate_register_returns_contract_error_shape():
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    client.post("/auth/register", json={"email": email, "password": "testpass123"})
    res = client.post("/auth/register", json={"email": email, "password": "testpass123"})
    assert res.status_code == 409
    body = res.json()
    # contract rule #3: exact { "error": { "code", "message" } } shape
    assert set(body.keys()) == {"error"}
    assert set(body["error"].keys()) == {"code", "message"}


def test_analyze_requires_auth():
    res = client.post("/analyze", files={"video": ("clip.mp4", b"fake", "video/mp4")}, data={"sportType": "badminton"})
    assert res.status_code == 401
    assert set(res.json().keys()) == {"error"}


def test_analyze_rejects_invalid_sport_type():
    token = _register_and_login()
    res = client.post(
        "/analyze",
        headers={"Authorization": f"Bearer {token}"},
        files={"video": ("clip.mp4", b"fake", "video/mp4")},
        data={"sportType": "basketball"},  # not in the closed enum
    )
    assert res.status_code == 422
    assert set(res.json().keys()) == {"error"}


def test_analyze_returns_full_contract_shape():
    token = _register_and_login()
    res = client.post(
        "/analyze",
        headers={"Authorization": f"Bearer {token}"},
        files={"video": ("clip.mp4", b"fake", "video/mp4")},
        data={"sportType": "cricket_bowling"},
    )
    assert res.status_code == 200
    body = res.json()
    expected_keys = {
        "analysisId", "sportType", "actionLabel", "overallScore",
        "professionalComparison", "metrics", "jointAngles", "faults",
        "strengths", "recommendations", "createdAt",
    }
    assert set(body.keys()) == expected_keys
    assert body["sportType"] == "cricket_bowling"
    for fault in body["faults"]:
        assert set(fault.keys()) == {"type", "description", "frame"}
        assert fault["type"] in {"hard", "soft"}


def test_nutrition_plan_matches_contract_shape():
    res = client.get("/nutrition/plan", params={"sportType": "archery"})
    assert res.status_code == 200
    body = res.json()
    assert set(body.keys()) == {
        "sportType", "energySystemCategory", "macroGuidance",
        "foodSuggestions", "exercises", "disclaimer",
    }
