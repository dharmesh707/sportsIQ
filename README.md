# SportsIQ

AI-powered multi-sport coaching app — SIH college internal round build.
Video in → MediaPipe pose extraction → joint-angle computation → self-trained
classifier → hard/soft fault detection against a professional + personal
baseline. Self-hosted, no external LLM API for core analysis.

**`API_CONTRACT.md` at this repo's root is the single source of truth for
every request/response shape.** If your code and that file disagree, the
file is right — fix the code. Read it before writing anything that touches
a request/response boundary. See that file's own header for the full rules;
the two that matter most day to day:

1. All JSON is camelCase (backend handles this via a shared Pydantic base — see `backend/app/schemas/base.py`).
2. Every error response is `{ "error": { "code": "string", "message": "string" } }` — no exceptions, no bare strings.

## Repo layout

```
sportsiq/
├── API_CONTRACT.md        ← source of truth, read this first
├── backend/                ← FastAPI (this is Dharmesh's piece)
│   └── app/
│       ├── api/routers/     one file per contract section (auth, analyze, ...)
│       ├── schemas/         Pydantic models — mirror the contract 1:1
│       ├── models/          SQLAlchemy DB models
│       ├── services/        business logic, mock data generators
│       ├── database/        engine/session setup
│       ├── ml/               pose / angles / similarity / llm — Day 2+ work
│       └── tests/           contract smoke tests — run before every push
└── frontend/                ← React Native (Expo) — teammate 3's piece, TBD
```

## Backend — local setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # defaults are fine for local dev
uvicorn app.main:app --reload
```

Server runs at `http://127.0.0.1:8000`. Interactive docs at `/docs` (only
when `DEBUG=true`, which is the local default).

## Before every push (contract discipline)

```bash
pytest app/tests/test_contract_smoke.py -v
```

This isn't a full test suite — it's a fast tripwire that checks camelCase,
the error shape, and the `sport_type` enum on the endpoints that exist so
far. If it's red, don't push. Add a case here whenever you add or change an
endpoint.

Quick manual check against a running server:

```bash
curl -X POST http://127.0.0.1:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"testpass123"}'
```

## Current status (Day 1)

- Auth (register/login/me) — real, working, JWT + bcrypt, SQLite locally.
- `/analyze` — real auth + multipart handling, but returns **hardcoded mock
  `AnalysisResult` data** (see `services/mock_data.py`). No ML wired up yet —
  that's Day 2/3.
- `/history`, `/dashboard`, `/progress` — real endpoints, backed by an
  in-memory store for now (`services/mock_store.py`). `/dashboard` and
  `/progress` shapes are a **placeholder** — contract says they're
  "unchanged from v1.0" but the actual v1.0 backend code wasn't available
  when this was scaffolded. Port the real shape from the old BadmintonIQ
  repo before the frontend teammate builds heavily against these two.
- `/health-data/sync` + `/summary` — stub, in-memory. Real integration
  lands when Health Connect work (teammate 6) hands off.
- `/nutrition/plan` — **real rule-based logic**, not mocked (deterministic,
  no LLM call — see `services/nutrition_rules.py`). Macro numbers are a
  first-pass scaffold; sanity-check against real sports-nutrition sources
  before judges see exact figures.

## Known dependency gotcha (already fixed here, don't re-break it)

`bcrypt` is pinned to `4.0.1` in `requirements.txt`. Newer bcrypt (4.1+)
breaks `passlib==1.7.4` with a misleading "password cannot be longer than
72 bytes" error on the very first hash call — reads like a password-length
bug, is actually a version mismatch. If you ever run `pip install -U bcrypt`,
you'll hit this again.

## Team norm

Build against `API_CONTRACT.md` exactly — field names, `sport_type` values,
error shape. Need something different? Change the contract file first, in
the same PR as the code, then write the code. Not the other way around.
