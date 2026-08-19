"""
Run with: pytest app/tests/test_contract_smoke.py -v
This isn't a full test suite - it's a fast contract-drift tripwire. Run it
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
    res = client.post("/auth/register", json={"email": email, "password": "TestPass123"})
    assert res.status_code == 201
    return res.json()["accessToken"]


def test_register_response_is_camel_case():
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    res = client.post("/auth/register", json={"email": email, "password": "TestPass123"})
    body = res.json()
    # contract: accessToken + user{id, email, createdAt}, camelCase throughout
    assert "accessToken" in body
    assert set(body["user"].keys()) == {"id", "email", "createdAt"}
    assert "access_token" not in body  # snake_case must NOT leak through


def test_duplicate_register_returns_contract_error_shape():
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    client.post("/auth/register", json={"email": email, "password": "TestPass123"})
    res = client.post("/auth/register", json={"email": email, "password": "TestPass123"})
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
        # contract section 2: faults now carry faultCode + optional referenceSource
        assert set(fault.keys()) == {"faultCode", "type", "description", "frame", "referenceSource"}
        assert fault["type"] in {"hard", "soft"}
    # cricket_bowling's mock data always includes the ICC Law 24 hard fault
    hard_faults = [f for f in body["faults"] if f["type"] == "hard"]
    assert any(f["faultCode"] == "elbow_extension_excess" for f in hard_faults)
    assert any(f["referenceSource"] for f in hard_faults)


def test_nutrition_plan_matches_contract_shape():
    res = client.get("/nutrition/plan", params={"sportType": "archery"})
    assert res.status_code == 200
    body = res.json()
    assert set(body.keys()) == {
        "sportType", "energySystemCategory", "macroGuidance",
        "foodSuggestions", "exercises", "disclaimer",
    }


def test_dashboard_matches_contract_shape():
    token = _register_and_login()
    # zero-session case first - must be 200 with empty arrays, not 404 or 500
    res = client.get("/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    body = res.json()
    assert set(body.keys()) == {
        "summary", "sportBreakdown", "recentSessions", "topFaults", "recommendations",
    }
    assert set(body["summary"].keys()) == {
        "totalSessions", "sportsPracticed", "currentStreakDays", "lastSessionAt",
    }
    assert body["summary"]["totalSessions"] == 0
    assert body["recentSessions"] == []

    # now with a real session
    client.post(
        "/analyze",
        headers={"Authorization": f"Bearer {token}"},
        files={"video": ("clip.mp4", b"fake", "video/mp4")},
        data={"sportType": "tennis"},
    )
    res = client.get("/dashboard", headers={"Authorization": f"Bearer {token}"})
    body = res.json()
    assert body["summary"]["totalSessions"] == 1
    assert body["summary"]["sportsPracticed"] == ["tennis"]
    assert len(body["recentSessions"]) == 1
    assert set(body["recentSessions"][0].keys()) == {
        "sessionId", "sportType", "score", "hardFaultCount", "softFaultCount", "createdAt",
    }
    if body["sportBreakdown"]:
        assert set(body["sportBreakdown"][0].keys()) == {
            "sportType", "sessionCount", "averageScore", "lastSessionAt", "trend",
        }
        assert body["sportBreakdown"][0]["trend"] == "insufficient_data"  # only 1 session


def test_dashboard_requires_auth():
    res = client.get("/dashboard")
    assert res.status_code == 401
    assert set(res.json().keys()) == {"error"}


def test_progress_requires_sport_type_query_param():
    token = _register_and_login()
    res = client.get("/progress", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 422


def test_progress_matches_contract_shape():
    token = _register_and_login()
    # zero-session case - must be 200 with empty arrays, not 404
    res = client.get(
        "/progress",
        headers={"Authorization": f"Bearer {token}"},
        params={"sportType": "tennis"},
    )
    assert res.status_code == 200
    body = res.json()
    assert set(body.keys()) == {
        "sportType", "range", "baseline", "dataPoints", "faultTrends",
    }
    assert set(body["range"].keys()) == {"start", "end"}
    assert set(body["baseline"].keys()) == {
        "initialScore", "currentScore", "percentChange", "establishedAt",
    }
    assert body["dataPoints"] == []
    assert body["faultTrends"] == []

    # now with a real session in that sport
    client.post(
        "/analyze",
        headers={"Authorization": f"Bearer {token}"},
        files={"video": ("clip.mp4", b"fake", "video/mp4")},
        data={"sportType": "tennis"},
    )
    res = client.get(
        "/progress",
        headers={"Authorization": f"Bearer {token}"},
        params={"sportType": "tennis"},
    )
    body = res.json()
    assert len(body["dataPoints"]) == 1
    assert set(body["dataPoints"][0].keys()) == {
        "date", "sessionId", "score", "hardFaultCount", "softFaultCount",
    }
    for trend in body["faultTrends"]:
        assert set(trend.keys()) == {"faultCode", "faultType", "occurrences"}
        assert trend["faultType"] in {"hard", "soft"}

