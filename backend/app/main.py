from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import analyze, auth, dashboard, health_data, history, nutrition
from app.config import get_settings
from app.database.session import Base, engine
from app.utils.errors import register_exception_handlers

settings = get_settings()

# Dev convenience only: creates SQLite tables on startup if missing. Once on
# real Postgres/Supabase, use Alembic migrations instead of this — swap out
# before Day 3 when the schema actually needs to evolve (PersonalBaseline,
# SkillCard, etc. per the brief's v1.1 section).
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="SportsIQ API",
    version="0.1.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(",") if settings.cors_origins != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(auth.router)
app.include_router(analyze.router)
app.include_router(history.router)
app.include_router(dashboard.router)
app.include_router(health_data.router)
app.include_router(nutrition.router)


@app.get("/health", tags=["meta"])
def health_check() -> dict[str, bool]:
    # Plain platform liveness check (Railway pings this) — deliberately NOT
    # under the contract's error/response envelope since it's not a contract
    # endpoint, just infra plumbing.
    return {"ok": True}
