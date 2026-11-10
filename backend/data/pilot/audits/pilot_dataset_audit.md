# SportsIQ Pilot Dataset Audit

## Result

The populated pilot annotation file is **not yet buildable** by the canonical
dataset pipeline. The canonical manifest is empty, and the populated
annotation CSV uses an earlier schema and `pending_review` status.

No videos, annotations, labels, timestamps, or source files were modified. No
model was trained.

## Inputs and project-root resolution

- Canonical manifest: [`stroke_manifest.csv`](../manifests/stroke_manifest.csv)
  — header only, 0 records.
- Populated annotations: [`stroke_annotations_pilot.csv`](../manifests/stroke_annotations_pilot.csv)
  — 16 rows.
- Dataset root used for canonical relative paths: `backend`.
- Referenced video: [`badminton_highlights.mp4`](../source_videos/badminton_highlights.mp4).
- Presence review: [`presence_review.csv`](../manifests/presence_review.csv)
  — 10 reviewed frame decisions; it is not a stroke manifest.

The populated CSV columns are:

```text
annotation_id,video_path,stroke_label,start_ms,end_ms,annotation_status,reviewer_id
```

The canonical manifest requires:

```text
clip_id,clip_path,stroke_label,source_video_id,player_id,session_id,
start_ms,end_ms,split,annotation_status,reviewer_id
```

## Dataset inventory

| Metric | Result |
|---|---:|
| Source videos | 1 |
| Annotated clips | 16 |
| Labels | `smash`: 16 |
| Players | Not represented |
| Sessions | Not represented |
| Splits | Not represented |
| Annotation statuses | `pending_review`: 16 |
| Source-video split leakage | Not assessable; no split field |
| Player split leakage | Not assessable; no player field |

### Source video

| Path | Resolution | FPS | Frames | Duration |
|---|---:|---:|---:|---:|
| `data/pilot/source_videos/badminton_highlights.mp4` | 1918×1078 | 30.0 | 1831 | 61.033 s |

MediaPipe full-body extraction succeeded in memory for all 1,831 frames.

The current full-body extractor reports:

| Player-presence value | Frames |
|---|---:|
| `PLAYER_PRESENT` | 1741 |
| `PLAYER_ABSENT` | 90 |
| `UNCERTAIN` | 0 |

This is the extractor’s current automatic assignment from whether landmarks
were returned. It should not be treated as reviewed player-presence ground
truth; the separate presence-review policy says missing pose is not equivalent
to player absence.

## Annotation interval audit

All 16 intervals are positive and within the measured 61,033.33 ms video
duration. All produced at least two source frames under the existing
start-inclusive/end-exclusive slicer. Across clips, 300 sliced frames were
processed in memory.

One pair overlaps:

- `smash_20261110_183532_554611`: `[34500, 35400)`
- `smash_20261110_183515_586712`: `[35333, 35733)`

Overlap is not rejected by the current manifest validator, but it should be
reviewed because overlapping clips may duplicate temporal content.

## Per-clip pose coverage

“Full-body reliable frames” means every one of the 21 canonical keypoints was
valid after `preprocess_full_body_sequence()` with the default confidence
threshold `0.5`. “Detected any keypoint frames” means at least one canonical
keypoint was present. Invalid/low-confidence counts are over 21 keypoints per
frame.

| Clip ID | Interval ms | Frames | Source frame range | Any keypoint | Full-body reliable | Valid keypoints | Invalid/low |
|---|---:|---:|---:|---:|---:|---:|---:|
| `smash_20261110_183040_250353` | 6333–7166 | 25 | 190–214 | 25 | 6 | 506 | 19 |
| `smash_20261110_183223_962653` | 14966–15466 | 15 | 449–463 | 15 | 0 | 205 | 110 |
| `smash_20261110_183300_891977` | 18000–18433 | 13 | 540–552 | 13 | 5 | 259 | 14 |
| `smash_20261110_183335_227897` | 22133–22733 | 18 | 664–681 | 18 | 0 | 342 | 36 |
| `smash_20261110_183346_133914` | 23800–24300 | 15 | 714–728 | 15 | 0 | 293 | 22 |
| `smash_20261110_183410_866546` | 26566–27333 | 23 | 797–819 | 23 | 0 | 446 | 37 |
| `smash_20261110_183515_586712` | 35333–35733 | 12 | 1060–1071 | 12 | 0 | 228 | 24 |
| `smash_20261110_183532_554611` | 34500–35400 | 27 | 1035–1061 | 27 | 4 | 526 | 41 |
| `smash_20261110_184758_912038` | 43433–44266 | 25 | 1303–1327 | 25 | 8 | 506 | 19 |
| `smash_20261110_184805_318214` | 44700–45233 | 16 | 1341–1356 | 16 | 4 | 312 | 24 |
| `smash_20261110_184813_771985` | 45766–46200 | 13 | 1373–1385 | 13 | 13 | 273 | 0 |
| `smash_20261110_184824_803665` | 46600–47133 | 16 | 1398–1413 | 16 | 0 | 300 | 36 |
| `smash_20261110_184835_459375` | 48233–48933 | 21 | 1447–1467 | 21 | 16 | 436 | 5 |
| `smash_20261110_184843_384655` | 49333–50000 | 20 | 1480–1499 | 20 | 0 | 377 | 43 |
| `smash_20261110_184902_020739` | 51000–51700 | 21 | 1530–1550 | 21 | 0 | 392 | 49 |
| `smash_20261110_184944_440025` | 60133–60800 | 20 | 1804–1823 | 20 | 0 | 118 | 302 |

Aggregate quality counts:

- 300 sliced frames.
- 5,519 valid keypoint features out of 6,300.
- 781 invalid or low-confidence keypoint features.
- 56 frames with all 21 keypoints reliable.
- Every interval produced at least two frames, so temporal feature extraction
  itself succeeded for every populated annotation row in memory.

## Pipeline build result

The exact build attempts were:

```powershell
cd backend
python -c "from app.ml.dataset.orchestration import build_dataset_from_manifest
try: build_dataset_from_manifest('data/pilot/manifests/stroke_manifest.csv', dataset_root='.')
except Exception as e: print(type(e).__name__+': '+str(e))
try: build_dataset_from_manifest('data/pilot/manifests/stroke_annotations_pilot.csv', dataset_root='.')
except Exception as e: print(type(e).__name__+': '+str(e)"
```

Observed output:

```text
ValueError: Cannot build a dataset from an empty manifest.
ValueError: Manifest is missing required columns: clip_id, clip_path, player_id, session_id, source_video_id, split
```

The populated rows also use `pending_review`, while
`validate_dataset_record()` only permits reviewed records for dataset
construction. The populated file has no `source_video_id`, `player_id`,
`session_id`, or `split`, so source-video and player leakage cannot be
validated and the builder cannot receive those records without an explicit
metadata completion step.

The in-memory pose/feature chain succeeded for all 16 intervals, but that is
not equivalent to a successful final dataset build because the canonical
manifest and required metadata are absent.

## Commands executed

1. Inventory and metadata:

```powershell
python - <<'PY'
... 
```

Executed as a PowerShell here-string piped to Python; it measured CSV schemas,
row counts, and OpenCV video metadata.

2. Manifest-reader checks:

```powershell
cd backend
python -c "from app.ml.dataset.io import read_manifest_csv; ..."
```

3. Pipeline build attempts: command shown above.

4. In-memory full-body extraction and per-clip feature audit using:

```text
extract_full_body_pose_sequence
slice_canonical_pose_sequence
preprocess_full_body_sequence
extract_joint_angles
extract_full_body_temporal_features
```

No source or annotation files were changed, and no generated pose/features
dataset was persisted.

## Required follow-up before dataset construction

The pilot annotation rows need an explicit metadata-completion/review step:

- map `annotation_id` to canonical `clip_id`;
- set the canonical `clip_path` to the original source video path;
- assign stable `source_video_id`;
- assign `player_id` and `session_id`;
- assign train/validation/test `split` values after leakage review;
- change `annotation_status` to `reviewed` only after annotation review;
- retain the original start-inclusive/end-exclusive timestamps;
- decide whether the overlapping pair is intentional.

No label or timestamp was changed by this audit.
