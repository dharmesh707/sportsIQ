"""Tests for password strength validation on /auth/register."""
import uuid

from app.tests.test_contract_smoke import client


def _unique_email() -> str:
    return f"test_{uuid.uuid4().hex[:8]}@example.com"


def test_register_rejects_all_numeric_password():
    res = client.post(
        "/auth/register", json={"email": _unique_email(), "password": "12345678"}
    )
    assert res.status_code == 422
    assert set(res.json().keys()) == {"error"}


def test_register_rejects_all_lowercase_password():
    res = client.post(
        "/auth/register", json={"email": _unique_email(), "password": "lowercase1"}
    )
    assert res.status_code == 422


def test_register_rejects_password_with_no_digit():
    res = client.post(
        "/auth/register", json={"email": _unique_email(), "password": "NoDigitsHere"}
    )
    assert res.status_code == 422


def test_register_rejects_too_short_password():
    res = client.post(
        "/auth/register", json={"email": _unique_email(), "password": "Ab1"}
    )
    assert res.status_code == 422


def test_register_accepts_valid_strong_password():
    res = client.post(
        "/auth/register", json={"email": _unique_email(), "password": "ValidPass123"}
    )
    assert res.status_code == 201
