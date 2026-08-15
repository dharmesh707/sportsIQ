"""
Temporary in-memory store, keyed by user_id, so /history and /dashboard have
something real to return during Day 1-2 without needing the full Analysis
SQLAlchemy model + migration yet.

Replace this with a real `analyses` table (Postgres via Supabase, see brief
section 3 on the pooler connection string) once the ML pipeline is actually
producing results to persist — probably Day 2-3 alongside the sport-aware
/analyze work. Swapping it out should only touch this file and the two
routers that import it (analyze.py, history.py) — nothing else references
this module directly, on purpose.
"""

from collections import defaultdict

from app.schemas.analysis import AnalysisResult

_store: dict[str, list[AnalysisResult]] = defaultdict(list)


def save(user_id: str, result: AnalysisResult) -> None:
    _store[user_id].insert(0, result)  # newest first


def list_for_user(user_id: str) -> list[AnalysisResult]:
    return _store[user_id]
