"""MediaPipe pose-sequence extraction for badminton movement analysis."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Sequence

import cv2
import mediapipe as mp
import numpy as np

from app.ml.pose.presence import PlayerPresence

RacketSide = Literal["left", "right", "unknown"]
MODEL_PATH = Path(__file__).resolve().parents[3] / "models" / "pose_landmarker_full.task"

LANDMARK_INDICES = {
    "left_shoulder": 11,
    "right_shoulder": 12,
    "left_elbow": 13,
    "right_elbow": 14,
    "left_wrist": 15,
    "right_wrist": 16,
}


@dataclass(frozen=True)
class LandmarkSample:
    """A landmark and its detector metadata, including missingness."""

    present: bool
    x: float | None = None
    y: float | None = None
    z: float | None = None
    visibility: float | None = None
    presence: float | None = None


@dataclass(frozen=True)
class ArmPose:
    shoulder: LandmarkSample
    elbow: LandmarkSample
    wrist: LandmarkSample
    elbow_angle_degrees: float | None


@dataclass(frozen=True)
class PoseFrame:
    frame_index: int
    timestamp_ms: int
    left: ArmPose
    right: ArmPose
    player_presence: PlayerPresence = "UNCERTAIN"


@dataclass(frozen=True)
class PoseSequence:
    """Timestamped bilateral pose observations for later model training."""

    frames: tuple[PoseFrame, ...]
    fps: float
    racket_side: RacketSide


def safe_angle_degrees(
    first: Sequence[float],
    vertex: Sequence[float],
    last: Sequence[float],
) -> float | None:
    """Return a finite 3D angle, or None when the geometry is invalid."""
    try:
        first_vector = np.asarray(first, dtype=float) - np.asarray(vertex, dtype=float)
        last_vector = np.asarray(last, dtype=float) - np.asarray(vertex, dtype=float)
    except (TypeError, ValueError):
        return None
    if first_vector.shape != last_vector.shape or not np.all(np.isfinite(first_vector)):
        return None
    if not np.all(np.isfinite(last_vector)):
        return None
    denominator = np.linalg.norm(first_vector) * np.linalg.norm(last_vector)
    if not np.isfinite(denominator) or denominator <= 0:
        return None
    cosine = np.dot(first_vector, last_vector) / denominator
    if not np.isfinite(cosine):
        return None
    return math.degrees(math.acos(float(np.clip(cosine, -1.0, 1.0))))


def calculate_elbow_angle(
    shoulder: LandmarkSample,
    elbow: LandmarkSample,
    wrist: LandmarkSample,
) -> float | None:
    """Calculate an elbow angle only when all three landmarks are valid."""
    points = (shoulder, elbow, wrist)
    if not all(point.present and point.x is not None and point.y is not None and point.z is not None
               for point in points):
        return None
    return safe_angle_degrees(
        (shoulder.x, shoulder.y, shoulder.z),
        (elbow.x, elbow.y, elbow.z),
        (wrist.x, wrist.y, wrist.z),
    )


def _landmark(landmarks, name: str) -> LandmarkSample:
    index = LANDMARK_INDICES[name]
    if index >= len(landmarks):
        return LandmarkSample(present=False)
    landmark = landmarks[index]
    values = (getattr(landmark, "x", None), getattr(landmark, "y", None), getattr(landmark, "z", None))
    coordinates = tuple(_finite_float(value) for value in values)
    visibility = _confidence(getattr(landmark, "visibility", None))
    presence = _confidence(getattr(landmark, "presence", None))
    if any(value is None for value in coordinates):
        return LandmarkSample(
            present=False,
            visibility=visibility,
            presence=presence,
        )
    return LandmarkSample(
        present=True,
        x=coordinates[0],
        y=coordinates[1],
        z=coordinates[2],
        visibility=visibility,
        presence=presence,
    )


def _arm_pose(landmarks, side: str) -> ArmPose:
    shoulder = _landmark(landmarks, f"{side}_shoulder")
    elbow = _landmark(landmarks, f"{side}_elbow")
    wrist = _landmark(landmarks, f"{side}_wrist")
    return ArmPose(
        shoulder=shoulder,
        elbow=elbow,
        wrist=wrist,
        elbow_angle_degrees=calculate_elbow_angle(shoulder, elbow, wrist),
    )


def _finite_float(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _confidence(value: object) -> float | None:
    number = _finite_float(value)
    return number if number is not None and 0.0 <= number <= 1.0 else None


def _validate_fps(fps: float) -> float:
    if not math.isfinite(fps) or fps <= 0:
        raise ValueError(
            f"Video FPS must be a finite positive value for timestamped pose extraction; got {fps!r}"
        )
    return fps


def _timestamp_ms(frame_index: int, fps: float, previous: int | None) -> int:
    _validate_fps(fps)
    timestamp = round(frame_index * 1000 / fps)
    return max(timestamp, (previous + 1) if previous is not None else 0)


def extract_pose_sequence(
    video_path: str | Path,
    racket_side: RacketSide = "unknown",
    model_path: Path = MODEL_PATH,
) -> PoseSequence:
    """Extract bilateral arm poses without selecting contact frames."""
    if racket_side not in {"left", "right", "unknown"}:
        raise ValueError("racket_side must be 'left', 'right', or 'unknown'")
    if not model_path.exists():
        raise FileNotFoundError(f"MediaPipe model not found: {model_path}")

    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise ValueError(f"Could not open video: {video_path}")
    try:
        fps = _validate_fps(float(capture.get(cv2.CAP_PROP_FPS)))
    except ValueError:
        capture.release()
        raise
    frames: list[PoseFrame] = []
    frame_index = 0
    previous_timestamp: int | None = None
    try:
        base_options = mp.tasks.BaseOptions(model_asset_path=str(model_path))
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
                timestamp_ms = _timestamp_ms(frame_index, fps, previous_timestamp)
                previous_timestamp = timestamp_ms
                image = mp.Image(
                    image_format=mp.ImageFormat.SRGB,
                    data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB),
                )
                detection = landmarker.detect_for_video(image, timestamp_ms)
                landmarks = detection.pose_landmarks[0] if detection.pose_landmarks else []
                frames.append(PoseFrame(
                    frame_index=frame_index,
                    timestamp_ms=timestamp_ms,
                    left=_arm_pose(landmarks, "left"),
                    right=_arm_pose(landmarks, "right"),
                ))
                frame_index += 1
    finally:
        capture.release()
    return PoseSequence(frames=tuple(frames), fps=fps, racket_side=racket_side)


def slice_pose_sequence(
    sequence: PoseSequence,
    start_ms: int,
    end_ms: int,
) -> PoseSequence:
    """Return pose frames within an annotation interval.

    Frame indices and timestamps remain on the original video timeline.
    The interval is start-inclusive and end-exclusive: ``[start_ms, end_ms)``.
    """
    if start_ms < 0:
        raise ValueError("start_ms must be >= 0")

    if end_ms <= start_ms:
        raise ValueError("end_ms must be greater than start_ms")

    selected_frames = tuple(
        frame
        for frame in sequence.frames
        if start_ms <= frame.timestamp_ms < end_ms
    )

    return PoseSequence(
        frames=selected_frames,
        fps=sequence.fps,
        racket_side=sequence.racket_side,
    )
