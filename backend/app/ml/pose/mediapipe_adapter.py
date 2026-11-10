"""Convert MediaPipe pose landmarks into SPORTSIQ canonical observations."""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

from app.ml.pose.canonical import (
    CANONICAL_KEYPOINT_NAMES,
    CoordinateMetadata,
    FramePoseObservation,
    KeypointObservation,
)
from app.ml.pose.presence import PlayerPresence


MEDIAPIPE_LANDMARK_INDICES: dict[str, int] = {
    "nose": 0,
    "left_eye": 2,
    "right_eye": 5,
    "left_ear": 7,
    "right_ear": 8,
    "left_shoulder": 11,
    "right_shoulder": 12,
    "left_elbow": 13,
    "right_elbow": 14,
    "left_wrist": 15,
    "right_wrist": 16,
    "left_hip": 23,
    "right_hip": 24,
    "left_knee": 25,
    "right_knee": 26,
    "left_ankle": 27,
    "right_ankle": 28,
    "left_heel": 29,
    "right_heel": 30,
    "left_foot_index": 31,
    "right_foot_index": 32,
}


def _finite_float(value: Any) -> float | None:
    """Return a finite float, or None for invalid values."""
    if isinstance(value, bool):
        return None

    try:
        number = float(value)
    except (TypeError, ValueError):
        return None

    return number if math.isfinite(number) else None


def _confidence(value: Any) -> float | None:
    """Return a valid confidence value in [0, 1]."""
    number = _finite_float(value)

    if number is None or not 0.0 <= number <= 1.0:
        return None

    return number


def _convert_landmark(landmark: Any) -> KeypointObservation:
    """Convert one MediaPipe landmark into a canonical observation."""
    x = _finite_float(getattr(landmark, "x", None))
    y = _finite_float(getattr(landmark, "y", None))
    z = _finite_float(getattr(landmark, "z", None))

    visibility = _confidence(
        getattr(landmark, "visibility", None)
    )
    presence = _confidence(
        getattr(landmark, "presence", None)
    )

    # x/y are required for a usable image-space observation.
    if x is None or y is None:
        return KeypointObservation(
            present=False,
            visibility=visibility,
            presence=presence,
        )

    return KeypointObservation(
        present=True,
        x_norm=x,
        y_norm=y,
        z_native=z,
        visibility=visibility,
        presence=presence,
        source_x=x,
        source_y=y,
        source_coordinate_system="mediapipe_normalized_image",
    )


def mediapipe_landmarks_to_frame(
    landmarks: Sequence[Any] | None,
    *,
    frame_index: int,
    timestamp_ms: int,
    width_px: int,
    height_px: int,
    player_presence: PlayerPresence = "UNCERTAIN",
) -> FramePoseObservation:
    """
    Convert one MediaPipe pose detection into a canonical frame.

    Missing detections and unavailable landmarks are represented explicitly.
    """
    landmark_list = landmarks or []

    keypoints: dict[str, KeypointObservation] = {}

    for name in CANONICAL_KEYPOINT_NAMES:
        index = MEDIAPIPE_LANDMARK_INDICES[name]

        if index >= len(landmark_list):
            keypoints[name] = KeypointObservation.missing()
            continue

        keypoints[name] = _convert_landmark(
            landmark_list[index]
        )

    return FramePoseObservation(
        frame_index=frame_index,
        timestamp_ms=timestamp_ms,
        width_px=width_px,
        height_px=height_px,
        keypoints=keypoints,
        player_presence=player_presence,
    )