
import pytest
from pydantic import ValidationError

from app.config import DEV_SECRET_KEY, Settings


def test_development_defaults_are_allowed():
    settings = Settings(_env_file=None)

    assert settings.debug is True
    assert settings.secret_key == DEV_SECRET_KEY
    assert settings.cors_origins == "*"


def test_production_rejects_development_secret():
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        Settings(
            _env_file=None,
            debug=False,
            cors_origins="https://app.example.com",
        )


def test_production_rejects_short_secret():
    with pytest.raises(ValidationError, match="at least 32 characters"):
        Settings(
            _env_file=None,
            debug=False,
            secret_key="too-short-secret",
            cors_origins="https://app.example.com",
        )


def test_production_rejects_wildcard_cors():
    with pytest.raises(ValidationError, match="CORS_ORIGINS"):
        Settings(
            _env_file=None,
            debug=False,
            secret_key="a" * 40,
            cors_origins="*",
        )


def test_production_accepts_explicit_secret_and_origins():
    settings = Settings(
        _env_file=None,
        debug=False,
        secret_key="a" * 40,
        cors_origins="https://app.example.com, https://admin.example.com",
    )

    assert settings.debug is False
    assert settings.secret_key == "a" * 40
    assert settings.cors_origins == (
        "https://app.example.com, https://admin.example.com"
    )
