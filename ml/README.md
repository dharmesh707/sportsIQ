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

## Badminton pose sequences

`backend/app/ml/pose/sequence.py` provides `extract_pose_sequence()` for
bilateral shoulder, elbow, and wrist observations. Each `PoseFrame` contains
the source frame index, a monotonically increasing timestamp, landmark
coordinates, visibility/presence metadata, missing-landmark state, and nullable
left/right elbow angles. The sequence also records `racket_side` as `left`,
`right`, or `unknown`.

This layer only extracts pose observations. It does not select a contact frame,
emit technique labels, or provide model confidence.

### Offline validation

From `backend/`, validate a local clip and write a CSV plus elbow-angle plot:

```powershell
python -m app.ml.scripts.validate_pose_sequence path\to\clip.mp4 `
  --racket-side unknown --output-dir path\to\pose-review
```

The CSV preserves unavailable angles and confidence values as empty fields.
The plot leaves unavailable angles as gaps. Plot generation requires
`matplotlib`; this tool does not calculate contact frames or technique labels.

### Visual pose diagnostics

Review a saved sequence against its original video:

```powershell
python -m app.ml.scripts.diagnose_pose_sequence `
  path\to\clip.mp4 path\to\clip_pose_sequence.csv `
  --output-dir path\to\diagnostic-frames
```

Use `n`/Right Arrow and `p`/Left Arrow to navigate, `s` to jump to the next
angle jump, `e` to export the current annotated frame, and `q` or Escape to
quit. By default, it opens validation frames `33 46 47 48 135 136 137`; use
`--frames` to provide a different list. It displays bilateral landmarks,
2D/3D elbow angles, and visibility/presence metadata. The tool highlights
consecutive angle changes greater than 30 degrees.

### Temporal depth diagnostics

Export right-arm model-relative depth and angle diagnostics for an inclusive
frame range:

```powershell
python -m app.ml.scripts.analyze_temporal_depth `
  path\to\pose_sequence.csv `
  --output-dir path\to\depth-review `
  --frame-range 37 68
```

MediaPipe `z` values are model-relative and are not calibrated physical depth.
The output is for comparing temporal patterns only; it does not establish
which elbow-angle calculation is correct.

### Temporal feature extraction

`backend/app/ml/features/temporal.py` provides
`extract_temporal_features(PoseSequence)` for offline, per-frame feature
generation. Coordinates are normalized MediaPipe x/y values. Wrist velocity is
normalized-coordinate units per second; wrist displacement is normalized
coordinate distance; elbow angular velocity is signed degrees per second; and
shoulder elevation is the image-plane angle from the shoulder to wrist, with
positive values upward. The first frame has no derivative features.

Missing landmarks, missing angles, unknown racket side, and non-positive
timestamp intervals produce `None`, never interpolation. Overall and
racket-arm quality status/reasons are carried into every feature frame.
The existing 3D elbow angle is retained as an optional diagnostic feature;
the initial temporal representation is otherwise 2D-first and is not a
trained classifier.

Export features for an existing validation clip and pose-sequence CSV from
`backend/`:

```powershell
python -m app.ml.scripts.export_temporal_features `
  path\to\validation.mp4 path\to\pose_sequence.csv `
  --output-dir path\to\temporal-features `
  --racket-side right --frame-range 37 68
```

The exporter writes one row per selected frame and a four-panel diagnostic
plot. It computes the full sequence before applying the optional range so the
first selected row can retain derivative context from the preceding frame.
Missing values remain empty in the CSV and appear as gaps in plots.
