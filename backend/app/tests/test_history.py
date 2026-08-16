"""Tests for GET /history - contract section 2.4 (pagination + fault counts)."""
from app.tests.test_contract_smoke import _register_and_login, client


def _create_analysis(token: str, sport: str = "badminton"):
    return client.post(
        "/analyze",
        headers={"Authorization": f"Bearer {token}"},
        files={"video": ("clip.mp4", b"fake", "video/mp4")},
        data={"sportType": sport},
    )


def test_history_empty_state():
    token = _register_and_login()
    res = client.get("/history", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    body = res.json()
    assert body["analyses"] == []
    assert body["pagination"] == {"page": 1, "pageSize": 20, "totalItems": 0, "totalPages": 0}


def test_history_returns_fault_counts_and_full_summary_shape():
    token = _register_and_login()
    _create_analysis(token, "cricket_bowling")  # mock data always has 1 hard + 1 soft fault
    res = client.get("/history", headers={"Authorization": f"Bearer {token}"})
    body = res.json()
    assert len(body["analyses"]) == 1
    item = body["analyses"][0]
    assert set(item.keys()) == {
        "analysisId", "sportType", "actionLabel", "overallScore",
        "hardFaultCount", "softFaultCount", "createdAt",
    }
    assert item["hardFaultCount"] == 1
    assert item["softFaultCount"] == 1


def test_history_pagination_splits_correctly():
    token = _register_and_login()
    for _ in range(5):
        _create_analysis(token)

    res = client.get("/history", headers={"Authorization": f"Bearer {token}"}, params={"pageSize": 2})
    body = res.json()
    assert len(body["analyses"]) == 2
    assert body["pagination"] == {"page": 1, "pageSize": 2, "totalItems": 5, "totalPages": 3}

    res_page2 = client.get(
        "/history", headers={"Authorization": f"Bearer {token}"}, params={"page": 2, "pageSize": 2}
    )
    assert len(res_page2.json()["analyses"]) == 2

    res_page3 = client.get(
        "/history", headers={"Authorization": f"Bearer {token}"}, params={"page": 3, "pageSize": 2}
    )
    assert len(res_page3.json()["analyses"]) == 1  # remainder


def test_history_sport_type_filter():
    token = _register_and_login()
    _create_analysis(token, "badminton")
    _create_analysis(token, "tennis")
    _create_analysis(token, "badminton")

    res = client.get(
        "/history", headers={"Authorization": f"Bearer {token}"}, params={"sportType": "tennis"}
    )
    body = res.json()
    assert body["pagination"]["totalItems"] == 1
    assert body["analyses"][0]["sportType"] == "tennis"


def test_history_requires_auth():
    res = client.get("/history")
    assert res.status_code == 401
