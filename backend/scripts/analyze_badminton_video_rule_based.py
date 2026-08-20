"""
Rule-based badminton biomechanics analysis for a local video file.

PRODUCTION. This is the active badminton path used by POST /analyze. It is
CV + geometry + explicit rules - there is no trained classifier in this file
and there is not meant to be one. See docs/TECHNIQUE_METHODOLOGY.md.

Pipeline:
    video -> MediaPipe PoseLandmarker (VIDEO mode, 1 pose)
          -> per-frame landmarks
          -> wrist-velocity peak => contact frame
          -> contact-frame joint angles
          -> rule-based shot classification
          -> reference-profile comparison (app.services.technique)

--------------------------------------------------------------------------
v2 FIX - why every real analysis used to score 0.0
--------------------------------------------------------------------------
v1 measured three of the five features with one convention while the
template numbers assumed a different one:

  * torso_inclination was measured from the HORIZONTAL axis, so a perfectly
    upright torso read as 90 deg - against a template value of 12. That is a
    guaranteed 78 deg error on every clip, no matter how good the form.
  * shoulder_elevation was the image-plane bearing of the shoulder->wrist
    vector, which reads ~75 deg for a normal overhead shot, against a
    template value of 25.
  * hip_shoulder_separation used MediaPipe's `z`, which is scale-ambiguous
    and collapses to 90 deg whenever z is near zero.

Combined with a harsh linear score (100 - mean_abs_diff * 2, which floors at
0 for a mean error of only 50 deg), a textbook smash scored 24.8 and most
real clips scored 0.0. Reproduced in
app/tests/test_technique_angles.py::test_v1_convention_bug_is_fixed.

v2 measures every feature against a documented convention, and those
conventions are restated in data/reference_profiles.json so the two cannot
drift apart again. Similarity is now per-feature with its own tolerance, so
one bad feature can no longer zero out the whole score.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np

# Allow `python scripts/analyze_badminton_video_rule_based.py <video>` to run
# standalone from backend/ as well as being imported by the FastAPI app.
_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

import mediapipe as mp  # noqa: E402

from app.services.technique import comparison as technique_comparison  # noqa: E402
from app.services.technique.config import (  # noqa: E402
    MAX_VIDEO_FRAMES,
    MAX_VIDEO_SECONDS,
    MIN_DETECTED_FRAMES,
    MIN_VIDEO_DIMENSION,
    MIN_VIDEO_FRAMES,
    POSE_QUALITY_REJECT_BELOW,
)

MODEL_PATH = _BACKEND_ROOT / "models" / "pose_landmarker_full.task"

_LANDMARKS = {
    "left_shoulder": 11,
    "right_shoulder": 12,
    "right_elbow": 14,
    "right_wrist": 16,
    "left_hip": 23,
    "right_hip": 24,
    "right_knee": 26,
    "right_ankle": 28,
}

# Wrist-velocity threshold (normalised image units per frame) above which the
# swing is treated as a smash-speed action. Pre-existing value, preserved.
_SMASH_VELOCITY = 0.08


class VideoError(ValueError):
    """Video could not be opened, decoded, or is outside supported limits."""


class InsufficientPoseError(ValueError):
    """Pose was detected in too few frames for the result to mean anything."""


# --------------------------------------------------------------------------
# Geometry
# --------------------------------------------------------------------------


def _angle(first: np.ndarray, vertex: np.ndarray, last: np.ndarray) -> float:
    """Interior angle at `vertex`, in degrees, 0-180."""
    first_vector = first - vertex
    last_vector = last - vertex
    denominator = float(np.linalg.norm(first_vector) * np.linalg.norm(last_vector))
    if denominator == 0:
        return float("nan")  # degenerate - excluded downstream, never scored as 0
    cosine = float(np.clip(np.dot(first_vector, last_vector) / denominator, -1.0, 1.0))
    return math.degrees(math.acos(cosine))


def _point(landmarks, name: str) -> np.ndarray:
    landmark = landmarks[_LANDMARKS[name]]
    return np.array([landmark.x, landmark.y, landmark.z], dtype=float)


def _wrap_to_quadrant(degrees_value: float) -> float:
    """
    Fold an angle difference between two undirected lines into 0-90.

    A shoulder line at +170 deg and one at -175 deg are 15 deg apart, not
    345. Without this, left/right landmark ordering flips would produce
    nonsense separation values.
    """
    wrapped = abs(degrees_value) % 180.0
    return 180.0 - wrapped if wrapped > 90.0 else wrapped


def _frame_angles(landmarks) -> dict[str, float]:
    """
    Contact-frame features. Conventions here MUST match the ones documented
    in app/services/technique/data/reference_profiles.json.

    MediaPipe image coordinates: x right, y DOWN, both normalised 0-1.
    """
    left_shoulder = _point(landmarks, "left_shoulder")
    right_shoulder = _point(landmarks, "right_shoulder")
    right_elbow = _point(landmarks, "right_elbow")
    right_wrist = _point(landmarks, "right_wrist")
    left_hip = _point(landmarks, "left_hip")
    right_hip = _point(landmarks, "right_hip")
    right_knee = _point(landmarks, "right_knee")
    right_ankle = _point(landmarks, "right_ankle")

    # Elbow: interior angle shoulder-elbow-wrist. 180 = fully extended.
    elbow_angle = _angle(right_shoulder, right_elbow, right_wrist)

    # Shoulder elevation: upper-arm segment above the horizontal, measured at
    # the shoulder. y is negated because image y grows downward. Positive =
    # elbow above shoulder, negative = elbow dropped below the shoulder line.
    upper_arm_dx = right_elbow[0] - right_shoulder[0]
    upper_arm_dy = right_elbow[1] - right_shoulder[1]
    shoulder_elevation = math.degrees(math.atan2(-upper_arm_dy, abs(upper_arm_dx)))

    # Knee: interior angle hip-knee-ankle. 180 = fully extended.
    knee_angle = _angle(right_hip, right_knee, right_ankle)

    # Hip-shoulder separation: image-plane bearing difference between the
    # shoulder line and the hip line. 2D only - MediaPipe's z is not metric
    # and using it here is what made this feature meaningless in v1.
    shoulder_bearing = math.degrees(
        math.atan2(right_shoulder[1] - left_shoulder[1], right_shoulder[0] - left_shoulder[0])
    )
    hip_bearing = math.degrees(
        math.atan2(right_hip[1] - left_hip[1], right_hip[0] - left_hip[0])
    )
    hip_shoulder_separation = _wrap_to_quadrant(shoulder_bearing - hip_bearing)

    # Torso inclination: deviation of the hip->shoulder axis from VERTICAL.
    # 0 = perfectly upright. This is the feature that was 78 deg wrong in v1.
    mid_shoulder = (left_shoulder + right_shoulder) / 2.0
    mid_hip = (left_hip + right_hip) / 2.0
    torso_dx = mid_shoulder[0] - mid_hip[0]
    torso_dy = mid_shoulder[1] - mid_hip[1]
    torso_inclination = math.degrees(math.atan2(abs(torso_dx), abs(torso_dy)))

    return {
        "elbow_angle": elbow_angle,
        "shoulder_elevation": shoulder_elevation,
        "knee_angle": knee_angle,
        "hip_shoulder_separation": hip_shoulder_separation,
        "torso_inclination": torso_inclination,
    }


def _classify_shot(angles: dict[str, float], wrist_peak: float) -> str:
    """
    Rule-based coarse shot classification. PRESERVED from v1 - same rules,
    same five labels, same ordering. Only the NaN guard is new.

    These are coarse biomechanical buckets, NOT the six-class dataset
    vocabulary. Do not swap in an experimental classifier here without
    cross-match evaluation.
    """
    knee = angles.get("knee_angle")
    elevation = angles.get("shoulder_elevation")
    elbow = angles.get("elbow_angle")

    def ok(v) -> bool:
        return v is not None and not math.isnan(v)

    if wrist_peak > _SMASH_VELOCITY and ok(knee) and knee < 150:
        return "JUMP_SMASH"
    if wrist_peak > _SMASH_VELOCITY:
        return "STICK_SMASH"
    if ok(elevation) and elevation > 45:
        return "FH_CLEAR"
    if ok(elbow) and elbow < 120:
        return "FH_DROP"
    return "FH_DRIVE"


# --------------------------------------------------------------------------
# Video probing
# --------------------------------------------------------------------------


def probe_video(video_path: str | Path) -> dict:
    """
    Cheap metadata read before spending CPU on pose inference.

    Raises VideoError with a message safe to show a user. CAP_PROP_FRAME_COUNT
    is a container hint and is sometimes wrong or zero, so zero is treated as
    "unknown" rather than "empty" - the real count comes from the decode loop.
    """
    capture = cv2.VideoCapture(str(video_path))
    try:
        if not capture.isOpened():
            raise VideoError(
                "This video could not be opened. It may be corrupted or in a "
                "format the analyzer does not support."
            )
        fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
        reported_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)

        ok, _ = capture.read()
        if not ok:
            raise VideoError(
                "This video could not be decoded. Try re-exporting it as an MP4 "
                "and uploading again."
            )
    finally:
        capture.release()

    if width and height and min(width, height) < MIN_VIDEO_DIMENSION:
        raise VideoError(
            f"This video is too small to analyze ({width}x{height}). Record at "
            f"least {MIN_VIDEO_DIMENSION}px on the short side."
        )
    if reported_frames > MAX_VIDEO_FRAMES:
        raise VideoError(
            f"This clip is too long to analyze ({reported_frames} frames). Trim it "
            f"to a single shot - under {MAX_VIDEO_FRAMES} frames."
        )
    if fps > 0 and reported_frames > 0:
        duration = reported_frames / fps
        if duration > MAX_VIDEO_SECONDS:
            raise VideoError(
                f"This clip is too long to analyze ({duration:.0f}s). Trim it to a "
                f"single shot - under {MAX_VIDEO_SECONDS:.0f} seconds."
            )

    return {
        "fps": fps,
        "reported_frames": reported_frames,
        "width": width,
        "height": height,
    }


# --------------------------------------------------------------------------
# Main entry point
# --------------------------------------------------------------------------


def analyze(video_path: str | Path, template_name: str = "viktor_axelsen") -> dict:
    """
    Analyze a video and return JSON-serialisable detector output.

    Backward compatible: every key v1 returned is still returned with the same
    meaning. New keys (total_frames, width, height, closest_template,
    all_template_similarities, wrist_peak_velocity) are additive.

    `template_name` is retained for backward compatibility but is no longer a
    hard selection - v2 scores against EVERY reference profile and reports the
    closest. The named profile's score is still what `template_similarity`
    returns, so existing callers see no shape change.
    """
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            "MediaPipe pose model not found at models/pose_landmarker_full.task. "
            "See README 'Model file' for how to fetch it."
        )

    probe = probe_video(video_path)
    fps = probe["fps"]

    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise VideoError(f"Could not open video: {video_path}")

    frame_count = 0
    poses: list[tuple[int, object]] = []
    wrist_y: list[float] = []

    try:
        base_options = mp.tasks.BaseOptions(model_asset_path=str(MODEL_PATH))
        options = mp.tasks.vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_poses=1,
        )
        with mp.tasks.vision.PoseLandmarker.create_from_options(options) as landmarker:
            while True:
                ok, frame = capture.read()
                if not ok:
                    break
                if frame_count > MAX_VIDEO_FRAMES:
                    raise VideoError(
                        f"This clip is too long to analyze. Trim it to under "
                        f"{MAX_VIDEO_FRAMES} frames."
                    )
                timestamp_ms = int(frame_count * 1000 / fps) if fps else frame_count
                image = mp.Image(
                    image_format=mp.ImageFormat.SRGB,
                    data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB),
                )
                detection = landmarker.detect_for_video(image, timestamp_ms)
                frame_count += 1
                if detection.pose_landmarks:
                    landmarks = detection.pose_landmarks[0]
                    poses.append((frame_count - 1, landmarks))
                    wrist_y.append(float(landmarks[_LANDMARKS["right_wrist"]].y))
    finally:
        capture.release()

    if frame_count < MIN_VIDEO_FRAMES:
        raise VideoError(
            f"This clip only contains {frame_count} readable frames - too short to "
            f"analyze. Record at least a full swing."
        )

    detection_rate = len(poses) / frame_count if frame_count else 0.0
    if len(poses) < MIN_DETECTED_FRAMES or detection_rate < POSE_QUALITY_REJECT_BELOW:
        raise InsufficientPoseError(
            f"Insufficient pose detection: {len(poses)} detected frames out of "
            f"{frame_count} ({detection_rate:.1%})"
        )

    velocity = np.abs(np.diff(np.asarray(wrist_y, dtype=float)))
    contact_index = int(np.argmax(velocity) + 1) if velocity.size else 0
    contact_index = min(contact_index, len(poses) - 1)
    contact_frame, contact_landmarks = poses[contact_index]

    raw_angles = _frame_angles(contact_landmarks)
    # NaN survives to here deliberately: comparison.py excludes non-finite
    # features rather than scoring them as a zero-similarity match.
    angles = {
        key: (round(value, 1) if not math.isnan(value) else float("nan"))
        for key, value in raw_angles.items()
    }

    wrist_peak = float(velocity.max()) if velocity.size else 0.0
    shot_type = _classify_shot(angles, wrist_peak)

    result = technique_comparison.compare(angles)
    if result is None:
        technique_score = 0.0
        template_similarity = 0.0
        all_similarities: dict[str, float] = {}
        closest = None
    else:
        all_similarities = {m.profile_id: m.similarity for m in result.all_matches}
        template_similarity = all_similarities.get(template_name, result.overall_similarity)
        technique_score = result.overall_similarity
        closest = result.closest.profile_id

    return {
        # --- v1 keys, unchanged meaning ---
        "video": str(video_path),
        "fps": fps,
        "detected_frames": len(poses),
        "detection_rate": round(detection_rate, 4),
        "contact_frame": contact_frame,
        "shot_type": shot_type,
        "angles": {k: (None if math.isnan(v) else v) for k, v in angles.items()},
        "technique_score": round(technique_score, 1),
        "template": template_name,
        "template_similarity": round(template_similarity, 1),
        # --- v2 additive keys ---
        "total_frames": frame_count,
        "width": probe["width"],
        "height": probe["height"],
        "wrist_peak_velocity": round(wrist_peak, 4),
        "closest_template": closest,
        "all_template_similarities": all_similarities,
    }


def _main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the production badminton detector on a local video file."
    )
    parser.add_argument("video", help="Path to a video file")
    parser.add_argument("--template", default="viktor_axelsen")
    args = parser.parse_args()

    try:
        output = analyze(args.video, args.template)
    except (VideoError, InsufficientPoseError, FileNotFoundError) as exc:
        print(json.dumps({"error": str(exc)}, indent=2))
        return 1
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
