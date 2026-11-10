# SportsIQ Pose Pipeline Audit (Phase 0)

## 1. Executive summary

The current reusable extractor is
[`extract_pose_sequence()`](../../app/ml/pose/sequence.py), using MediaPipe
PoseLandmarker in VIDEO mode with the local
`models/pose_landmarker_full.task` asset. It processes every readable video
frame, keeps zero-based frame indices, and preserves missing landmarks and
confidence metadata.

The most important correctness finding is that the extractor calculates a
nominal 3D elbow angle from `detection.pose_landmarks`, which is the
MediaPipe normalized-image landmark collection. The installed MediaPipe result
API also exposes `pose_world_landmarks`, but the extractor does not use it.
Consequently, the current 3D angle combines normalized image `x`, `y`, and
image-space depth `z`; it should not be treated as a metric/world-space joint
angle without validation.

Other verified limitations:

- The extractor requests `num_poses=1`; it does not support multi-person
  tracking or identity selection.
- Missing pose results become missing bilateral arm landmarks. They are not
  distinguished from occlusion, player absence, or detector failure.
- `PlayerPresence` exists as a defaulted `PoseFrame` field and as a separate
  manual CSV helper, but `extract_pose_sequence()` does not load or apply a
  presence review.
- Only shoulder, elbow, and wrist landmarks for both arms are retained by the
  reusable extractor. This prevents direct lower-body, trunk, head, and
  racket/shuttle analysis from that data structure.
- The temporal exporter exports the requested/all rows from the pose CSV and
  does not automatically remove buffer footage.
- No RTMPose/YOLO-Pose integration or benchmark utility exists in the current
  repository.

No production code or existing report was modified by this audit. The only
created file is this report.

## 2. Current architecture and data flow

### Source video to pose sequence

[`extract_pose_sequence()`](../../app/ml/pose/sequence.py:172):

1. Validates `racket_side` and the model path.
2. Opens the video with `cv2.VideoCapture`.
3. Reads `CAP_PROP_FPS` and requires a finite positive FPS.
4. Reads frames sequentially with `capture.read()`.
5. Uses a zero-based `frame_index`.
6. Converts BGR frames to RGB `mp.Image` objects.
7. Calls `landmarker.detect_for_video(image, timestamp_ms)`.
8. Selects only `detection.pose_landmarks[0]` when a pose exists.
9. Extracts bilateral shoulder, elbow, and wrist landmarks.
10. Calculates one elbow angle for each arm.
11. Appends a `PoseFrame` even when no pose was detected.
12. Returns a `PoseSequence`.

The MediaPipe options are VIDEO mode, one pose, and the full model asset:
[`sequence.py:196-200`](../../app/ml/pose/sequence.py:196).

### Pose data structures

- [`LandmarkSample`](../../app/ml/pose/sequence.py:29) stores `present`,
  normalized coordinates, visibility, and presence.
- [`ArmPose`](../../app/ml/pose/sequence.py:42) stores shoulder, elbow, wrist,
  and an elbow angle.
- [`PoseFrame`](../../app/ml/pose/sequence.py:50) stores frame/timestamp,
  both arms, and `player_presence`.
- [`PoseSequence`](../../app/ml/pose/sequence.py:59) stores ordered frames,
  FPS, and racket side.

`PoseFrame.player_presence` defaults to `UNCERTAIN`, but extraction always
constructs the frame without applying a reviewed decision, so extraction
currently leaves it at that default.

### Downstream feature path

[`extract_temporal_features()`](../../app/ml/features/temporal.py:146) selects
the configured racket arm and derives nullable 2D coordinates, angles,
shoulder elevation, wrist displacement/velocity, angular velocity, confidence,
and quality fields. It does not use `player_presence`.

[`export_temporal_features()`](../../app/ml/scripts/export_temporal_features.py:248)
loads a pose CSV, computes features over the full loaded sequence, then selects
an optional inclusive frame range. It does not detect or exclude buffer
footage.

### API path

The FastAPI route
[`analyze()`](../../app/api/routers/analyze.py:21) calls
[`run_pipeline()`](../../app/ml_pipeline.py:51), which routes badminton to
[`analyze_badminton_video()`](../../app/services/badminton_analysis.py:8).
That service imports the separate rule-based script
[`analyze()`](../../scripts/analyze_badminton_video_rule_based.py:53).

The API production path therefore does not use the reusable
`app.ml.pose.sequence` extractor. The rule-based script independently uses
MediaPipe normalized landmarks, right-arm-only logic, hardcoded professional
templates, and wrist-Y displacement for contact-frame selection.

## 3. Findings ranked by severity

### High — current 3D elbow angle is not a world-space angle

**Files/functions**

- [`sequence.py:213`](../../app/ml/pose/sequence.py:213) passes
  `detection.pose_landmarks[0]` to `_arm_pose()`.
- [`sequence.py:91`](../../app/ml/pose/sequence.py:91)
  `calculate_elbow_angle()` passes `x`, `y`, and `z` to
  `safe_angle_degrees()`.

The installed MediaPipe API was inspected directly. Its
`PoseLandmarkerResult` annotations expose:

```text
pose_landmarks: list[list[mediapipe.tasks.python.components.containers.landmark.NormalizedLandmark]]
pose_world_landmarks: list[list[mediapipe.tasks.python.components.containers.landmark.Landmark]]
segmentation_masks: Optional[list[...]]
```

The extractor uses `pose_landmarks`, whose coordinates are normalized image
landmarks. Its `z` is not a metric world-coordinate axis. Combining that
depth-like value with normalized image `x` and `y` produces a geometrically
computable vector, but not a validated physical 3D joint angle. The existing
2D angle diagnostic is separately calculated from normalized image `x/y` in
[`validate_pose_sequence.py:85`](../../app/ml/scripts/validate_pose_sequence.py:85).

**Impact:** current `elbow_angle_degrees` should be treated as a diagnostic
image-normalized angle, not as a world-space biomechanical measurement.

### High — no automatic distinction between player absence and pose failure

At [`sequence.py:213`](../../app/ml/pose/sequence.py:213), an empty detection
becomes `landmarks = []`. `_landmark()` returns `LandmarkSample(present=False)`
at [`sequence.py:108-111`](../../app/ml/pose/sequence.py:108). The same
representation is used for missing individual landmarks.

The quality layer
[`assess_frame_quality()`](../../app/ml/pose/quality.py:83) reports missing,
low-confidence, and out-of-frame landmark reasons, but it does not classify
player presence.

The reviewed presence helper
[`load_presence_review()`](../../app/ml/pose/presence.py:28) is a separate
CSV loader. No call site passes its mapping into extraction, and no extraction
step changes `PoseFrame.player_presence` from its default.

### High — only one person is requested

[`sequence.py:196-200`](../../app/ml/pose/sequence.py:196) sets
`num_poses=1`, then [`sequence.py:213`](../../app/ml/pose/sequence.py:213)
selects pose index zero. There is no person identity, tracking, player
selection, or handling of multiple detections.

### Medium — reusable pose representation is upper-limb-only

[`LANDMARK_INDICES`](../../app/ml/pose/sequence.py:18) contains only shoulders,
elbows, and wrists for left and right sides. This is sufficient for the
current elbow-focused diagnostic, but prevents direct analysis from the
reusable sequence of hips, knees, ankles, torso, head, feet, or other
landmark-based movement features.

The separate legacy rule-based script extracts a few additional right-side
landmarks (hips, knee, ankle) at
[`analyze_badminton_video_rule_based.py:11-21`](../../scripts/analyze_badminton_video_rule_based.py:11),
but that data is not part of `PoseSequence`.

### Medium — no automatic buffer-footage exclusion

[`export_temporal_features()`](../../app/ml/scripts/export_temporal_features.py:248)
computes features from the full loaded CSV and uses
[`select_feature_frames()`](../../app/ml/scripts/export_temporal_features.py:109)
only when an explicit inclusive range is supplied. No presence status or
continuous-player interval is consulted. A broad range or no range can
therefore include unrelated buffer rows.

### Medium — current quality is strict bilateral quality, not racket-arm quality

[`assess_frame_quality()`](../../app/ml/pose/quality.py:83) combines reasons
from both arms. A missing non-racket arm makes overall frame quality
unreliable, while [`assess_arm_roles()`](../../app/ml/pose/quality.py:56)
separately reports racket-arm quality when racket side is known. This is
appropriate as a diagnostic distinction but should not be interpreted as
player absence or overall pose usability for every downstream task.

### Low — confidence is preserved at extraction but thresholding is downstream

[`_confidence()`](../../app/ml/pose/sequence.py:156) converts non-finite or
out-of-range values to `None`, preserving valid values. Extraction itself does
not reject low confidence; the default `0.5` threshold is applied by the
quality module at [`quality.py:9`](../../app/ml/pose/quality.py:9) and its
callers.

### Low — legacy API path has weaker timestamp behavior

The reusable extractor validates FPS and enforces strictly increasing
timestamps at [`sequence.py:147-164`](../../app/ml/pose/sequence.py:147).
The legacy rule-based script uses:

```python
timestamp_ms = int(frame_count * 1000 / fps) if fps else frame_count
```

at [`analyze_badminton_video_rule_based.py:84`](../../scripts/analyze_badminton_video_rule_based.py:84).
It has a fallback to frame indices when FPS is zero and does not use the
reusable timestamp helper.

## 4. Diagnostic output: what the reported numbers measure

The recent artifact
`backend/data/validation/quality_check/f0724262-de53-46ba-88dc-3fed18758ee1_pose_sequence.csv`
contains 159 rows. Recomputing its fields produced:

- `114/159` rows with a non-empty left elbow angle.
- `114/159` rows with a non-empty right elbow angle.
- `114/159 = 71.698...%`, conventionally reported as `71.7%`.
- Maximum consecutive valid right-angle change: `64.1376116994096°`,
  between frames `136` and `137`.
- Right-angle changes strictly greater than `30°`: `10`.
- Missing right-angle ranges: `106–121`, `127–134`, `138–158`.

These are measurements of the saved CSV's angle availability and consecutive
angle differences. They are not:

- pose-estimation accuracy
- player-presence accuracy
- landmark ground-truth accuracy
- technique-classification accuracy
- contact-frame accuracy
- benchmark performance across videos

The missing ranges are ranges where the right elbow angle field is empty.
They are consistent with missing required landmarks in the exported artifact,
but do not prove that the player was absent.

## 5. Verified versus uncertain

### Verified

- The reusable extractor uses MediaPipe PoseLandmarker VIDEO mode.
- The model path is `backend/models/pose_landmarker_full.task`.
- The model asset exists and is 9,398,198 bytes.
- Frames are read sequentially and indexed from zero.
- FPS must be finite and positive in the reusable extractor.
- Timestamps are forced to be strictly increasing integers.
- Only `detection.pose_landmarks[0]` is used.
- Missing landmarks and invalid confidence values are represented as missing
  values/`None`.
- Quality uses a default visibility/presence threshold of `0.5`.
- Both arms' shoulder, elbow, and wrist landmarks are retained.
- Pose resources are released: `VideoCapture` is released in a `finally` block,
  and MediaPipe landmarker uses a context manager.
- The existing focused pose/diagnostic/temporal tests passed:

```text
44 passed in 2.32s
```

- The full backend suite previously run in this repository passed 116 tests
  with one symlink-related skip; that result is recorded in the existing
  `backend/data/benchmark/REPORT.md`.

### Uncertain or not established

- No manually labeled landmark ground truth exists to establish angle accuracy.
- No validated player-presence ground truth exists.
- The reported diagnostic values do not establish model accuracy.
- No controlled comparison against RTMPose or YOLO-Pose exists.
- The current repository does not contain `backend/scripts/pose_benchmark.py`
  or `backend/app/tests/test_pose_benchmark.py`.
- Whether normalized image-space `z` is useful for this specific diagnostic
  cannot be established as a physical angle without a controlled validation;
  it is not equivalent to MediaPipe world landmarks.
- The saved diagnostic CSVs are artifacts from prior runs; their exact command
  provenance is not encoded in the CSV itself.

## 6. Tests, model configuration, and alternatives

### Existing pose-related tests

- [`test_pose_sequence.py`](../../app/tests/test_pose_sequence.py): safe angle
  handling, bilateral arm extraction, missing landmarks, confidence
  sanitization, FPS validation, timestamps, CSV preservation, and 2D angle
  diagnostics.
- [`test_pose_quality.py`](../../app/tests/test_pose_quality.py): threshold,
  missingness, out-of-frame coordinates, coverage, racket/non-racket roles,
  and unknown racket side.
- [`test_pose_presence.py`](../../app/tests/test_pose_presence.py): reviewed
  status loading, default uncertainty, intervals, gaps, and invalid statuses.
- [`test_pose_diagnostic.py`](../../app/tests/test_pose_diagnostic.py):
  timestamp synchronization, angle-jump detection, frame selection, and CLI
  argument parsing.
- [`test_temporal_features.py`](../../app/tests/test_temporal_features.py):
  nullable temporal feature behavior and derivatives.
- [`test_temporal_feature_export.py`](../../app/tests/test_temporal_feature_export.py):
  CSV reconstruction, inclusive selection, and exporter parsing.

The focused command run for this audit was:

```powershell
cd backend
pytest -q app\tests\test_pose_sequence.py app\tests\test_pose_quality.py app\tests\test_pose_presence.py app\tests\test_pose_diagnostic.py app\tests\test_temporal_features.py app\tests\test_temporal_feature_export.py -rs
```

Result:

```text
44 passed in 2.32s
```

Pytest emitted the existing unrelated `RequestsDependencyWarning`.

### MediaPipe model and configuration

- Asset: `backend/models/pose_landmarker_full.task`
- Reusable extractor: `PoseLandmarkerOptions`, `RunningMode.VIDEO`,
  `num_poses=1`
- Legacy rule-based script uses the same asset and also sets `num_poses=1`.

### RTMPose and YOLO-Pose

No repository integration was found for RTMPose or YOLO-Pose. The requested
benchmark module is absent. Previous experiment dependencies may be installed
in the user environment, but that is not an integration or a benchmark.

The current `backend/requirements.txt` lists MediaPipe, OpenCV, NumPy, and
Matplotlib, but not RTMPose or Ultralytics.

The existing dependency environment also reports unrelated package conflicts
from previous experiments:

```text
crawl4ai 0.8.6 has requirement pydantic>=2.10, but you have pydantic 2.9.2.
grpcio-status 1.71.2 has requirement protobuf<6.0dev,>=5.26.1, but you have protobuf 4.25.9.
langchain-community 0.4.1 has requirement pydantic-settings<3.0.0,>=2.10.1, but you have pydantic-settings 2.5.2.
opentelemetry-proto 1.40.0 has requirement protobuf<7.0,>=5.0, but you have protobuf 4.25.9.
realtime 2.28.0 has requirement pydantic<3.0.0,>=2.11.7, but you have pydantic 2.9.2.
storage3 2.28.0 has requirement pydantic>=2.11.7, but you have pydantic 2.9.2.
```

No installation or upgrade was performed during this audit.

## 7. Recommended fixes, in priority order

1. **Correctly separate image and world geometry.** Preserve normalized image
   coordinates for image diagnostics, and only calculate a world-space elbow
   angle from `pose_world_landmarks` when the required landmarks are present.
   Keep the existing public structures compatible, or add clearly named
   fields rather than silently changing the meaning of
   `elbow_angle_degrees`.
2. **Make presence review explicit at the sequence/export boundary.** Keep
   player presence separate from pose quality, apply reviewed frame-index
   decisions explicitly, and prevent automatic inference of
   `PLAYER_ABSENT` from missing landmarks.
3. **Add deterministic benchmark tooling before comparing estimators.** Define
   one frame-indexed benchmark output, controlled timing, model versions,
   overlay output, and a reviewed presence/landmark evaluation protocol.
4. **Decide whether the reusable sequence must include full-body landmarks.**
   Add them only after the badminton baseline requirements are defined; do not
   silently expand the current arm-only contract.
5. **Unify or clearly isolate the API's legacy rule-based path.** The API
   currently does not use the reusable extractor and has different angle,
   timestamp, presence, and missing-data behavior.
6. **Add multi-person policy and tests.** Either continue to require one person
   with an explicit documented assumption or implement deterministic identity
   selection before using multi-person footage.

## 8. Safe implementation plan preserving current contracts

1. Add internal conversion helpers that retain both normalized image landmarks
   and optional world landmarks without changing API response schemas.
2. Preserve existing `PoseFrame`, `ArmPose`, and CSV columns initially; add new
   world-angle output only under an explicitly versioned diagnostic field.
3. Keep `player_presence` review metadata separate from landmark quality and
   require an explicit review mapping keyed by original frame index.
4. Add unit tests for normalized-versus-world coordinate selection, missing
   world landmarks, multi-person handling policy, and resource cleanup.
5. Add an offline benchmark script outside the FastAPI request path. It should
   compare estimators on identical frames and report runtime/completeness only
   until manually labeled ground truth exists.
6. Preserve `/analyze`, auth, and frontend contracts. Do not route the API to a
   new estimator or change result fields until the offline baseline is
   independently validated.
7. Run focused pose tests, benchmark utility tests, and the full backend suite
   after implementation. No classifier training should be part of this phase.
