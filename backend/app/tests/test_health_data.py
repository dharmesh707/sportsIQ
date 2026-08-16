"""Contract smoke coverage for /health-data - optional enrichment layer."""
from app.tests.test_contract_smoke import _register_and_login, client


def test_health_summary_empty_state_is_200_not_404():
    token = _register_and_login()
    res = client.get("/health-data/summary", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    body = res.json()
    assert body == {"steps": 0, "heartRateAvg": 0, "activeMinutes": 0, "lastSyncedAt": None}


def test_health_sync_then_summary_roundtrip():
    token = _register_and_login()
    sync_res = client.post(
        "/health-data/sync",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "steps": 8500,
            "heartRateAvg": 72.5,
            "activeMinutes": 45,
            "syncedAt": "2026-08-17T06:00:00Z",
        },
    )
    assert sync_res.status_code == 200
    assert sync_res.json() == {"ok": True}

    summary_res = client.get("/health-data/summary", headers={"Authorization": f"Bearer {token}"})
    body = summary_res.json()
    assert body["steps"] == 8500
    assert body["heartRateAvg"] == 72.5
    assert body["activeMinutes"] == 45
    assert body["lastSyncedAt"] is not None


def test_health_sync_rejects_negative_steps():
    token = _register_and_login()
    res = client.post(
        "/health-data/sync",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "steps": -100,
            "heartRateAvg": 72.5,
            "activeMinutes": 45,
            "syncedAt": "2026-08-17T06:00:00Z",
        },
    )
    assert res.status_code == 422
    assert set(res.json().keys()) == {"error"}


def test_health_data_requires_auth():
    res = client.get("/health-data/summary")
    assert res.status_code == 401
