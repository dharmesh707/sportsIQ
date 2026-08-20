from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

settings = get_settings()

# check_same_thread only matters for SQLite; harmless to pass unconditionally
# guarded by the URL check below.
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_v2_columns() -> None:
    """
    Add v2 analysis columns to an existing SQLite file if they are missing.

    Base.metadata.create_all() creates missing TABLES but never adds a column
    to a table that already exists, so a developer pulling this change onto a
    machine with an existing sportsiq.db would get "no such column" on every
    /history call. This is a deliberately minimal, additive, idempotent
    forward-only shim - not a migration system.

    When this project moves to Postgres, delete this and use Alembic. It only
    runs for SQLite and only ever issues ADD COLUMN.
    """
    if not settings.database_url.startswith("sqlite"):
        return

    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    if "analyses" not in inspector.get_table_names():
        return  # create_all() will build it fresh with every column already present

    existing = {col["name"] for col in inspector.get_columns("analyses")}
    additions = {
        "weaknesses": "JSON",
        "pose_quality": "JSON",
        "athlete_comparison": "JSON",
        "feature_comparison": "JSON",
        "detailed_recommendations": "JSON",
        "data_source": "VARCHAR",
    }
    missing = {name: ddl for name, ddl in additions.items() if name not in existing}
    if not missing:
        return

    with engine.begin() as connection:
        for name, ddl in missing.items():
            connection.execute(text(f"ALTER TABLE analyses ADD COLUMN {name} {ddl}"))
