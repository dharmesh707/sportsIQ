
"""
Application settings.

Development defaults are convenient for local use.
Production requires an explicit signing secret and explicit CORS origins.
"""

from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


DEV_SECRET_KEY = "dev-only-change-me-before-deploy"
MIN_PRODUCTION_SECRET_LENGTH = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    # Database
    database_url: str = "sqlite:///./sportsiq.db"

    # Authentication
    secret_key: str = DEV_SECRET_KEY
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7

    # Application
    cors_origins: str = "*"
    debug: bool = True

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        # Development settings may use convenient defaults.
        if self.debug:
            return self

        # Production must not use the development signing key.
        if self.secret_key == DEV_SECRET_KEY:
            raise ValueError(
                "SECRET_KEY must be explicitly configured when DEBUG=false."
            )

        # Require a sufficiently long secret.
        if len(self.secret_key) < MIN_PRODUCTION_SECRET_LENGTH:
            raise ValueError(
                "SECRET_KEY must contain at least 32 characters "
                "when DEBUG=false."
            )

        # Production must use explicit CORS origins.
        origins = [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]

        if not origins or "*" in origins:
            raise ValueError(
                "CORS_ORIGINS must contain explicit origins "
                "when DEBUG=false."
            )

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
