# ml/ — model pipeline

## Plug-and-play contract

Create `ml/sports/<sport_type>/classifier.py` with exactly one function:

    def analyze(video_bytes: bytes) -> AnalysisResult

Import `AnalysisResult` from `app.schemas.analysis` (backend is on your
Python path automatically - see backend/app/ml_pipeline.py). Populate every
field per API_CONTRACT.md - faultCode values must come from the contract's
section 2.2 table (extend-only: add new codes there in the same PR you add
them here).

`<sport_type>` matches the closed enum exactly: badminton, tennis,
table_tennis, cricket_bowling, archery.

The moment your `classifier.py` exists and defines `analyze()`, the backend
auto-detects and routes real video to it - no one needs to touch the router,
the contract, or ask you to ping them. Until your file exists, that sport
silently uses Day 1 mock data, so nothing breaks while you're still training.

## Folder layout

- `pose/` - MediaPipe extraction helpers (shared across sports)
- `angles/` - joint-angle computation from pose keypoints (shared)
- `sports/<sport>/` - your classifier.py per sport, plus whatever else you need
