# SPORTSIQ Canonical Full-Body Pose Schema Design

## Status and scope

This document is a design proposal only. The canonical full-body schema is not
implemented, and no production extractor, API contract, frontend behavior, or
benchmark semantics are changed by this document.

## 1. Current architecture

### Reusable extractor

[`sequence.py`](../../app/ml/pose/sequence.py) currently defines:

- `LandmarkSample` at line 29: `present`, normalized-image `x/y`, estimator
  `z`, and optional `visibility`/`presence`.
- `ArmPose` at line 42: shoulder, elbow, wrist, and one elbow angle.
- `PoseFrame` at line 50: zero-based `frame_index`, integer `timestamp_ms`,
  bilateral `ArmPose`, and reviewed `player_presence`.
- `PoseSequence` at line 59: ordered frames, FPS, and `racket_side`.

`LANDMARK_INDICES` at line 17 retains only landmarks 11–16: both shoulders,
elbows, and wrists. `extract_pose_sequence()` at line 172 reads every frame,
uses MediaPipe VIDEO mode, requests `num_poses=1`, and selects
`detection.pose_landmarks[0]`.

The current `calculate_elbow_angle()` at line 91 uses the normalized image
landmark `x/y/z` values. This is a finite geometric angle, but it is not a
calibrated physical 3D angle. MediaPipe world landmarks are not currently
stored by this extractor.

### Quality and presence

[`quality.py`](../../app/ml/pose/quality.py) assesses the retained bilateral
arm landmarks. `DEFAULT_CONFIDENCE_THRESHOLD` is `0.5`; missing coordinates,
missing/low visibility, missing/low presence, and out-of-frame x/y create
quality reasons. Quality is not player detection.

[`presence.py`](../../app/ml/pose/presence.py) defines:

- `PlayerPresence = PLAYER_PRESENT | PLAYER_ABSENT | UNCERTAIN`
- CSV review columns `frame_index,player_presence,notes`
- `present_intervals()` over original contiguous frame indices

Unreviewed frames default to `UNCERTAIN`. Presence must remain independent of
pose quality and must not be inferred from missing landmarks.

### Temporal consumers

[`temporal.py`](../../app/ml/features/temporal.py) consumes `PoseSequence` and
selects the configured racket arm. It currently produces nullable
shoulder/elbow/wrist coordinates, estimator-native z, 2D elbow angle,
diagnostic elbow angle, shoulder elevation, wrist velocity, angular velocity,
confidence metadata, and quality fields. It does not currently consume full
body landmarks or player presence.

### Benchmark output

[`pose_benchmark.py`](../../scripts/pose_benchmark.py) defines a separate
benchmark representation. `Keypoint.x/y` are now canonical normalized image
coordinates; `source_x/source_y` preserve estimator-native input values.
`Keypoint.z` remains estimator-native and is explicitly not comparable.
Benchmark metadata records source coordinate convention and frame dimensions.
The benchmark currently covers only six bilateral shoulder/elbow/wrist joints.

### Production API path

[`analyze.py`](../../app/api/routers/analyze.py) calls
[`run_pipeline()`](../../app/ml_pipeline.py), which routes badminton to
[`analyze_badminton_video()`](../../app/services/badminton_analysis.py).
That service imports the legacy
[`analyze()`](../../scripts/analyze_badminton_video_rule_based.py), not
`extract_pose_sequence()`. The legacy path is right-arm-oriented and
rule/template-based. The schema must therefore be introduced offline first.

## 2. Proposed canonical schema

### Keypoint vocabulary

The canonical full-body vocabulary is:

```text
nose
left_eye, right_eye
left_ear, right_ear
left_shoulder, right_shoulder
left_elbow, right_elbow
left_wrist, right_wrist
left_hip, right_hip
left_knee, right_knee
left_ankle, right_ankle
left_heel, right_heel
left_foot_index, right_foot_index
```

These names are stable, side-explicit, and map directly to the standard
MediaPipe Pose landmark indices. Additional face landmarks, hands, racket, and
shuttle are out of scope because the current pose model does not provide them
as this schema's supported keypoints.

### Sequence-level object

Proposed conceptual structure:

```json
{
  "schema_name": "sportsiq.canonical_pose",
  "schema_version": "1.0",
  "video": {
    "video_id": "review-assigned-id",
    "width_px": 608,
    "height_px": 1080,
    "fps": 25.99998183090019,
    "frame_count": 159
  },
  "estimator": {
    "name": "mediapipe",
    "package_version": "1.0.1",
    "model": "pose_landmarker_full.task",
    "num_poses": 1
  },
  "coordinate_policy": {
    "image_xy": "normalized_image",
    "x_norm": "x_px / width_px",
    "y_norm": "y_px / height_px",
    "z": "estimator_native",
    "world": "optional_estimator_native"
  },
  "racket_side": "unknown",
  "frames": [
    {
      "frame_index": 0,
      "timestamp_ms": 0,
      "player_presence": "UNCERTAIN",
      "keypoints": {
        "right_wrist": {
          "present": true,
          "x_norm": 0.5476,
          "y_norm": 0.3527,
          "z_native": -0.8521,
          "visibility": 0.9932,
          "presence": null,
          "source": {
            "x": 0.5476,
            "y": 0.3527,
            "coordinate_system": "normalized_image"
          }
        },
        "left_ankle": {
          "present": false,
          "x_norm": null,
          "y_norm": null,
          "z_native": null,
          "visibility": null,
          "presence": null,
          "source": null
        }
      }
    }
  ]
}
```

The example is illustrative, not a dataset record and not a claim that the
schema has been implemented.

### Keypoint field policy

| Field | Policy |
|---|---|
| `present` | True only when the adapter has valid x/y coordinates for that joint. |
| `x_norm`, `y_norm` | Canonical normalized image coordinates in `[0, 1]` when valid; otherwise `null`. Preserve out-of-frame finite values for diagnostics only if the schema validation policy permits them, but do not clamp them. |
| `z_native` | Optional estimator-native depth-like value. Never silently convert or compare it across estimators. |
| `visibility` | Optional estimator-provided visibility. MediaPipe visibility is not interchangeable with another estimator's score. |
| `presence` | Optional estimator-provided presence probability. Do not copy visibility into this field. |
| `confidence` | Optional adapter field only where the estimator explicitly provides a score. Never fabricate it from visibility or presence. |
| `source` | Optional raw x/y values and declared source coordinate system. Required for benchmark/debug adapters; may be omitted from compact training exports. |
| `world` | Optional world-coordinate object only when the estimator actually supplies it, with explicit units/frame metadata. |

Missing values are `null`; missing joints remain in the keypoint map rather
than being dropped. Invalid non-finite coordinates become missing and should
be accompanied by adapter diagnostics. A missing joint is not evidence of
`PLAYER_ABSENT`.

## 3. Coordinate and geometry policy

### Image coordinates

All adapters should expose canonical:

```text
x_norm = x_px / frame_width
y_norm = y_px / frame_height
```

MediaPipe normalized image coordinates can pass through unchanged, while pixel
outputs from YOLO-Pose and RTMPose must be divided by the decoded frame
dimensions. Original values and source units should remain available in raw
adapter output or debug metadata.

Do not clamp coordinates into `[0, 1]`; an out-of-frame finite point is useful
quality evidence. Schema validation can distinguish finite out-of-frame values
from absent values.

### z and world coordinates

`z_native` is estimator-specific. It must not be used as if it were a common
metric depth axis. MediaPipe `pose_landmarks.z` and
`pose_world_landmarks` are different representations.

World coordinates are optional and must include the estimator name, coordinate
frame, and units/scale declaration. If those declarations are unavailable,
retain the values as estimator-native and do not call derived angles physical.

### Angles and derived geometry

Every derived measurement must declare its geometry space:

- `angle_2d_image_degrees`: angle from canonical image x/y.
- `angle_3d_estimator_native_degrees`: angle from one estimator's native x/y/z,
  diagnostic only.
- `angle_3d_world_degrees`: only when all three points use the same declared
  world coordinate frame and units.

Normalized image-space angles are viewpoint-dependent. They are not physical
biomechanical measurements. Camera perspective, foreshortening, camera roll,
and lens distortion can change them. Calibrated physical measurements require
camera calibration and a declared coordinate model, neither of which currently
exists.

### Left/right identity

`left` and `right` mean the subject's anatomical sides as reported by the
estimator, not the viewer's screen sides. Adapters must preserve the estimator
mapping and record any estimator-specific mirroring configuration. No adapter
may infer racket side from motion or landmark confidence.

## 4. Temporal representation and missing data

- `frame_index` is the original zero-based decoded source-frame index.
- `timestamp_ms` is an integer, strictly increasing within a sequence.
- FPS must be finite and positive; no frame-index-as-millisecond fallback is
  allowed when FPS is unavailable.
- A sequence may be variable length and may contain a frame for every decoded
  source frame, including frames with no detected pose.
- `player_presence` is reviewed metadata keyed by original frame index and
  defaults to `UNCERTAIN`.
- Buffer footage is not silently removed. A movement/stroke window should be
  an explicit inclusive `[start_frame, end_frame]` selection or a separately
  reviewed present interval.
- Raw observations are immutable benchmark inputs. Interpolation and smoothing
  are derived layers with their own fields, parameters, and provenance.
- Default policy is no interpolation and no smoothing for raw exports.
- If interpolation is later used for a model feature, retain the raw null,
  mark the derived value as `imputed=true`, and record source frames and method.
- Missing frames break derivatives by default. A derivative must not bridge a
  missing/uncertain endpoint unless an explicit derived-data policy permits it.

## 5. Estimator adapter architecture

The proposed layers are:

1. **Decoder** — decodes each source frame once and owns frame index,
   timestamp, dimensions, and FPS.
2. **Estimator adapter** — runs MediaPipe, YOLO-Pose, or RTMPose and returns
   estimator-native raw points, scores, model metadata, and errors.
3. **Canonical mapper** — maps supported joints to stable names, converts image
   x/y to canonical normalized coordinates, preserves source values, and
   records unavailable joints.
4. **Schema validator** — validates required fields, finite values, dimensions,
   timestamp ordering, duplicate/missing indices, and declared coordinate
   systems.
5. **Quality layer** — evaluates visibility, confidence, out-of-frame points,
   missingness, person-selection status, and reviewed player presence without
   changing raw values.
6. **Derived feature layer** — computes explicit 2D/native-3D/world-space
   geometry and temporal features with provenance.
7. **Badminton analysis layer** — consumes canonical sequences plus reviewed
   movement/phase/contact annotations. It must not be part of the estimator
   adapter.

MediaPipe can map all listed vocabulary points from its full pose landmark
set. YOLO-Pose and RTMPose adapters should map only joints actually available
from their selected skeleton. Unavailable joints remain present as schema
entries with `present=false` and a reason such as `unsupported_by_skeleton`;
they must not be reconstructed from neighboring joints.

### Comparable and non-comparable fields

Genuinely comparable after mapping:

- source frame index and timestamp when the same decoder frames are used
- canonical normalized image x/y
- availability/missingness, with a shared definition
- finite image-space geometric features calculated from the canonical x/y

Not automatically comparable:

- estimator-native z/depth
- world coordinates from different frames/units
- visibility, presence, and confidence calibration
- first-person selection when multiple people exist
- jitter without accounting for missing-frame gaps and true movement
- physical biomechanics or technique quality

## 6. Testing strategy

Before any production migration, add isolated schema tests for:

1. Every canonical joint name and deterministic ordering.
2. MediaPipe index mapping for the full-body vocabulary.
3. Pixel-to-normalized and already-normalized coordinate conversion.
4. Preservation of source values and estimator-native z.
5. Invalid/non-finite coordinates and confidence becoming `null`.
6. Missing supported joints versus unsupported skeleton joints.
7. Zero-based frame indices and strict timestamp ordering.
8. Frame dimensions/aspect-ratio metadata.
9. No interpolation in raw output.
10. Explicit imputation provenance for any future derived layer.
11. Player presence remaining independent from pose quality.
12. Multi-person policy and deterministic selected-person metadata.

Golden fixtures should use synthetic coordinates and no fabricated confidence.
At least one fixture should contain a gap, an out-of-frame finite point, an
unsupported joint, and an uncertain presence interval.

## 7. Incremental migration and rollback

### Step 1 — isolated schema package

Introduce schema types and validation outside `app.ml.pose.sequence`, with
serialization tests. No existing dataclass changes.

**Rollback:** remove the new package and tests; current extractor and API are
unchanged.

### Step 2 — MediaPipe adapter

Map the full MediaPipe landmark set into the new schema, preserving both image
landmarks and optional world landmarks. Keep the existing arm extractor as the
reference path.

**Rollback:** stop invoking the adapter; retain current bilateral output.

### Step 3 — synthetic and artifact validation

Run schema validation on synthetic fixtures and a copied offline validation
video. Compare frame indices, timestamps, missingness, and existing arm
coordinates. Do not compare the current nominal 3D angle as a physical
ground truth.

**Rollback:** discard only offline schema artifacts.

### Step 4 — full-body benchmark output

Extend the isolated benchmark to emit all supported full-body joints and
explicit unsupported-joint reasons. Keep the existing six-joint output
versioned and readable.

**Rollback:** select the prior benchmark output version.

### Step 5 — optional alternative adapters

Add YOLO-Pose and RTMPose adapters only when local model artifacts and
documented skeleton mappings are available. Run identical decoded frames and
record package/model versions. Do not download models from the benchmark.

**Rollback:** mark the adapter unavailable; MediaPipe remains the baseline.

### Step 6 — later production integration decision

Only after reviewed presence/landmark data and compatibility tests should the
team consider using the schema in temporal features or the API. This is a
separate contract decision and is not part of this phase.

## 8. Unresolved decisions

1. Which canonical schema versioning and serialization format should be
   committed: JSONL, Parquet, or a typed Python/Arrow representation?
2. Should `present` mean valid x/y only, or require a minimum confidence
   threshold? The proposal uses valid x/y and leaves thresholding to quality.
3. What is the approved multi-person selection policy?
4. Should world landmarks be retained in the canonical schema or only in
   estimator-specific sidecars?
5. What confidence/visibility calibration policy is acceptable across
   estimators?
6. What camera calibration, if any, is available for physical measurements?
7. Which full-body joints are required for the first badminton pilot versus
   optional for later studies?
8. How are movement windows and contact annotations linked to canonical
   sequences?

## 9. Recommended next implementation task

Implement an isolated `canonical_pose` module under `backend/app/ml/pose/`
with:

- typed sequence/frame/keypoint metadata
- deterministic full-body MediaPipe index mapping
- canonical normalized x/y conversion
- explicit native z/world sidecars
- null-preserving missingness and confidence handling
- strict frame/timestamp validation
- synthetic tests for mapping, conversion, missingness, and presence

Do not change `sequence.py`, the API route, temporal formulas, or frontend
contracts in that task. Add an offline serializer and validator first, then
compare its arm subset against the existing extractor before any migration.
