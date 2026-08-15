"""
App-wide settings, loaded from environment variables (.env locally, Railway
dashboard vars in production). See .env.example at the repo root for the
full list this expects.

Reminder from the project brief (don't forget this again): Supabase Postgres
uses the TRANSACTION POOLER connection string (port 6543), not the direct
connection (port 5432). Get DATABASE_URL from Supabase's "Connection pooling"
tab, not the plain "Connection string" tab.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Local dev default: SQLite file, matches the existing dev environment
    # (apps/backend/badmintoniq.db in the old repo). Swap via env var when
    # deploying — Supabase pooler string goes here, port 6543.
    database_url: str = "sqlite:///./sportsiq.db"

    secret_key: str = "dev-only-change-me-before-deploy"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days, fine for hackathon demo

    cors_origins: str = "*"  # comma-separated in production, e.g. Expo dev URL + prod app scheme
    debug: bool = True  # gates Swagger /docs — set false in production per brief section 5


@lru_cache
def get_settings() -> Settings:
    return Settings()
