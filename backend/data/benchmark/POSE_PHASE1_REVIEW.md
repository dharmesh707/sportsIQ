# SportsIQ Phase 1 Benchmark Artifact Review

## Scope

This review covers the generated MediaPipe benchmark artifacts and the
benchmark implementation. It does not evaluate pose accuracy, because no
manually annotated landmark ground truth is available. It does not claim that
YOLO-Pose or RTMPose were benchmarked; neither produced inference results.

## 1. Artifacts located

The reviewed artifact set is:

- `backend/data/benchmark/pose_phase1_overlay/benchmark_report.json`
- `backend/data/benchmark/pose_phase1_overlay/mediapipe_frames.jsonl`
- `backend/data/benchmark/pose_phase1_overlay/mediapipe_overlay.mp4`

Additional earlier runs were present under:

- `backend/data/benchmark/pose_phase1/`
- `backend/data/benchmark/pose_phase1_all/`

The report reviewed here is the `pose_phase1_overlay` run because it includes
the overlay video.

## 2. Independently verified metrics

The report states a 608 x 1080 video at 25.99998183090019 FPS with 159 decoded
frames and a duration of 6.115388888888888 seconds. The JSONL independently
contains exactly 159 records:

```text
first frame/timestamp: 0, 0
last frame/timestamp: 158, 6077
indices contiguous: True
timestamps strictly increasing: True
```

The overlay MP4 independently opens as 608 x 1080, 26.0 FPS, and decodes
exactly 159 frames. Its frame count and ordering therefore align with the
JSONL's zero-based source-frame convention.

The JSONL independently reports:

```text
detected frames: 114
coverage: 114 / 159 = 71.6981% (71.7% rounded)
missing ranges: 106–121, 127–134, 138–158
errors: 0
```

`missing_detection_ranges` are inclusive ranges. They are produced by
`_ranges()` in `backend/scripts/pose_benchmark.py`, which emits both the first
and last index in each contiguous run.

All six common joints have 114 available coordinates in the reviewed output.
Missing-detection records contain `None` for coordinates, depth, and confidence.
The available confidence values are finite and within `[0, 1]`. These are
detector-provided confidence/visibility values, not accuracy scores.

## 3. Latency and FPS definitions

The report contains:

```text
mean latency: 28.482815098462616 ms
median latency: 29.53130006790161 ms
minimum: 14.828599989414215 ms
maximum: 64.25809999927878 ms
reported effective FPS: 35.10888922120538
processing duration: 6.212944800034165 s
```

The latency numbers are mathematically consistent with the JSONL records:
`1000 / 28.482815098462616 = 35.10888922120538`.

The timing boundary is `benchmark_estimator()` around the per-frame `infer`
call at `backend/scripts/pose_benchmark.py:338-349`. For MediaPipe, that
includes RGB conversion and `detect_for_video()` because both occur inside the
backend inference closure at `backend/scripts/pose_benchmark.py:157-164`.
It excludes model initialization, video decoding (all frames are decoded
before benchmarking), and JSONL serialization. With overlays enabled it also
does not include overlay drawing/writing in the per-frame latency, although
the aggregate `processing_duration_seconds` includes the loop and writer
release.

Therefore:

- `35.11 FPS` is inference-loop throughput derived from mean per-frame
  latency.
- It is not end-to-end application throughput.
- `6.2129` seconds is not full command runtime because decode and model
  initialization occur outside the timed interval.
- The overlay file uses the source FPS (about 26 FPS), not the measured
  inference FPS.

The timing labels are useful but should be made more explicit in a future
benchmark revision.

## 4. Jitter metric

`temporal_jitter_mean_abs_x` is calculated in
`_result_summary()` at `backend/scripts/pose_benchmark.py:244-254`. For each
joint it:

1. Keeps only frames where that joint has an `x` coordinate.
2. Removes all missing frames rather than preserving temporal gaps.
3. Computes the mean of `abs(x[i+1] - x[i])` over the remaining values.

For the MediaPipe run, `x` is normalized image-space `x`, so the values are
dimensionless normalized-coordinate changes. This is a useful rough
displacement summary, but it is not a temporal jitter score: it includes real
motion, does not account for frame-time gaps, and does not distinguish detector
noise from player movement. It should not be used as an estimator-quality
ranking metric without a stationary or labeled reference.

## 5. Overlay observations

The overlay was decoded and representative frames were inspected. The green
frame labels match the source frame sequence, and the video contains 159
frames.

Visual observations:

- Frames 0 and 50 show the player in the room with visible arm landmarks.
- Frames 100–105 are close-up views of the player; the detected points remain
  present but the framing is crowded.
- Frames 106–121 show a very close, blurred/occluded view of the arm/body. The
  JSONL reports no common keypoints in this interval.
- Frames 122–126 show blurred close-up/floor transition imagery with some
  landmarks returning.
- Frames 127–137 are mostly blurred floor/object imagery; the JSONL reports
  no detections for 127–134 and detections again around 135–137.
- Frames 138–158 show unrelated floor/room/buffer imagery and no common
  detections.

These observations support that the missing ranges correspond to difficult
visual content and later buffer footage in this particular video. They do not
prove whether each missing frame represents player absence, occlusion, motion
blur, or a pose-estimation failure. A reviewed presence annotation is still
required.

## 6. Benchmark defects and limitations

### Finding 1 — common coordinate representation is not common

**Severity: High**

`_from_points()` at `backend/scripts/pose_benchmark.py:127-148` stores input
`x` and `y` unchanged. MediaPipe supplies normalized coordinates, while the
YOLO path at `backend/scripts/pose_benchmark.py:181-187` passes
`keypoints.xy`, which is in image pixels. The RTMPose path similarly passes
the body output directly at `backend/scripts/pose_benchmark.py:197-200`.

Consequences if YOLO or RTMPose is run:

- JSONL coordinates would have different units from MediaPipe.
- Jitter values would not be comparable.
- Overlay rendering uses a heuristic (`x <= 1` and `y <= 1`) to decide
  normalized versus pixel coordinates at `_draw_overlay()`; this is not an
  explicit backend contract.

No incorrect MediaPipe result is caused by this finding, but cross-estimator
comparison is not currently valid. Before benchmarking alternatives, normalize
pixel coordinates using the decoded frame dimensions and record the source
coordinate convention.

### Finding 2 — estimator availability is model-file availability, not capability

**Severity: Low**

The run reports YOLO and RTMPose as unavailable because the default local model
paths do not exist. The packages were importable, but no inference was
performed. This is correctly reported as unavailable and no model was
downloaded. It should not be interpreted as package incompatibility or as a
performance comparison.

### Finding 3 — confidence semantics differ by backend

**Severity: Medium**

MediaPipe uses the landmark `visibility` field as its benchmark confidence at
`backend/scripts/pose_benchmark.py:160-162`. YOLO uses keypoint confidence,
and RTMPose uses the returned score. These values may not have identical
semantics or calibration. They are preserved, but cross-backend confidence
threshold comparisons would require an explicit policy.

### Finding 4 — no person identity or multi-person evaluation

**Severity: Medium**

MediaPipe is configured with `num_poses=1`; YOLO and RTMPose also select the
first returned person. The benchmark does not identify the badminton player
when multiple people are present and does not compare person selection across
estimators.

### Finding 5 — output does not include full per-frame source image metadata

**Severity: Low**

The JSONL preserves frame index and timestamp, but not frame width/height per
record. The report contains video dimensions globally, which is sufficient for
this fixed video but should be treated as part of the shared representation
when comparing videos or variable-size inputs.

## 7. Is MediaPipe sufficient for the next phase?

MediaPipe is sufficient for the next **data-quality and annotation phase**:
it provides reproducible frame-indexed output, bilateral arm keypoints,
confidence metadata, missingness, and an inspectable overlay. The output is
not sufficient to claim pose accuracy, physical 3D angle validity, player
presence, or badminton technique quality.

It is not yet sufficient for a fair estimator comparison because the
alternative backends lack local model artifacts and the common coordinate
normalization is incomplete.

## 8. Recommended next step

The next technically justified step is to create a small manually reviewed
benchmark fixture:

1. Mark player presence and uncertainty by original frame index.
2. Review a small set of shoulder, elbow, and wrist landmarks or accept/reject
   detections using an explicit annotation protocol.
3. Correct the benchmark's common coordinate conversion so every backend
   emits normalized image coordinates and records source units.
4. Provide local, versioned YOLO-Pose/RTMPose model artifacts only through an
   explicitly approved environment setup; do not download them as part of the
   benchmark.
5. Re-run all estimators on identical decoded frames and compare completeness,
   latency, and labeled quality separately.

Do not train a technique classifier or route any alternative estimator into the
production API as part of this step.

## 9. Commands and test results

The review used read-only artifact inspection and OpenCV decoding. No models
were downloaded and no dependencies were installed or changed.

Existing focused benchmark and pose tests were already run for this
implementation:

```text
49 passed in 2.54s
```

No source code was modified during this artifact review. The only repository
file created by this task is this report.

## 10. Phase 1.1 canonical-coordinate correction

The original Finding 1 above was confirmed in
`backend/scripts/pose_benchmark.py`: MediaPipe supplied normalized image
coordinates, while the YOLO and RTMPose adapters supplied pixel coordinates.

The benchmark now converts every backend's image coordinates to the canonical
representation:

```text
x_norm = x_px / frame_width
y_norm = y_px / frame_height
```

The canonical values remain in `Keypoint.x` and `Keypoint.y`. The original
finite source x/y values are preserved as `source_x` and `source_y`. The
benchmark JSON metadata records the source convention, canonical units, source
value fields, and frame dimensions. Overlay rendering now always consumes
canonical normalized coordinates rather than guessing units from their numeric
range.

The `z` value remains estimator-native. It is not converted or treated as
equivalent across MediaPipe, YOLO, and RTMPose, and no biomechanical
measurement is made from it.

A fresh MediaPipe run using the corrected benchmark was written to:

- `backend/data/benchmark/pose_phase1_canonical/benchmark_report.json`
- `backend/data/benchmark/pose_phase1_canonical/mediapipe_frames.jsonl`
- `backend/data/benchmark/pose_phase1_canonical/mediapipe_overlay.mp4`

It preserved the same 159 source frames, 114 detected frames, and inclusive
missing ranges as the prior run. MediaPipe's source and canonical x/y values
are equal because its source convention is already normalized. YOLO-Pose and
RTMPose still have no actual inference results in this repository, so their
cross-estimator output remains unvalidated.

After this correction, normalized x/y coordinate comparisons and the
dimensionless x-jitter calculation are technically comparable across
estimators, provided they process the same image dimensions and selected
person. Confidence semantics, z/depth values, person identity, temporal
motion versus detector jitter, and pose accuracy remain non-comparable or
unvalidated without additional policy and labeled ground truth.

## 11. Phase 1.1 validation

Focused canonical-coordinate tests:

```text
8 passed in 0.31s
```

Benchmark plus existing focused pose and temporal tests:

```text
52 passed in 1.51s
```

The existing `RequestsDependencyWarning` was emitted by the environment during
pytest. `git diff --check` was run after the changes and passed.
