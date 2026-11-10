"""Extract 2D joint-angle features from canonical full-body poses."""

from __future__ import annotations

import math
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from app.ml.pose.canonical import CanonicalPoseSequence


@dataclass(frozen=True)
class JointAngleFrame:
    """Joint angles associated with one source frame."""

    frame_index: int
    timestamp_ms: int
    angles_degrees: Mapping[str, float | None]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "angles_degrees",
            MappingProxyType(dict(self.angles_degrees)),
        )


@dataclass(frozen=True)
class JointAngleSequence:
    """Joint-angle features for a canonical pose sequence."""

    frames: tuple[JointAngleFrame, ...]
    fps: float | None

    feature_schema: str = "sportsiq.joint_angles"
    feature_version: str = "1.0"


# Each angle is defined by:
# (point A, vertex, point C)
#
# The angle is measured at the vertex.
JOINT_ANGLE_DEFINITIONS = {
    "left_elbow": (
        "left_shoulder",
        "left_elbow",
        "left_wrist",
    ),
    "right_elbow": (
        "right_shoulder",
        "right_elbow",
        "right_wrist",
    ),
    "left_shoulder": (
        "left_hip",
        "left_shoulder",
        "left_elbow",
    ),
    "right_shoulder": (
        "right_hip",
        "right_shoulder",
        "right_elbow",
    ),
    "left_hip": (
        "left_shoulder",
        "left_hip",
        "left_knee",
    ),
    "right_hip": (
        "right_shoulder",
        "right_hip",
        "right_knee",
    ),
    "left_knee": (
        "left_hip",
        "left_knee",
        "left_ankle",
    ),
    "right_knee": (
        "right_hip",
        "right_knee",
        "right_ankle",
    ),
}


def _reliable_point(
    observation,
    confidence_threshold: float,
) -> tuple[float, float] | None:
    """Return a reliable 2D point, or None when unavailable."""

    if not observation.present:
        return None

    x = observation.x_norm
    y = observation.y_norm

    if x is None or y is None:
        return None

    if not math.isfinite(x) or not math.isfinite(y):
        return None

    for value in (
        observation.visibility,
        observation.presence,
        observation.confidence,
    ):
        if value is not None and value < confidence_threshold:
            return None

    return x, y


def calculate_angle_degrees(
    point_a: tuple[float, float],
    vertex: tuple[float, float],
    point_c: tuple[float, float],
) -> float | None:
    """
    Calculate the unsigned 2D angle at the vertex.

    Returns an angle in [0, 180], or None if either vector has
    effectively zero length.
    """

    ax, ay = point_a
    vx, vy = vertex
    cx, cy = point_c

    vector_a = (ax - vx, ay - vy)
    vector_c = (cx - vx, cy - vy)

    length_a = math.hypot(*vector_a)
    length_c = math.hypot(*vector_c)

    if length_a <= 1e-12 or length_c <= 1e-12:
        return None

    dot_product = (
        vector_a[0] * vector_c[0]
        + vector_a[1] * vector_c[1]
    )

    cross_product = (
        vector_a[0] * vector_c[1]
        - vector_a[1] * vector_c[0]
    )

    angle = math.degrees(
        math.atan2(
            abs(cross_product),
            dot_product,
        )
    )

    if not math.isfinite(angle):
        return None

    return angle


def extract_joint_angles(
    sequence: CanonicalPoseSequence,
    *,
    confidence_threshold: float = 0.5,
) -> JointAngleSequence:
    """
    Extract 2D joint angles from a canonical full-body sequence.

    Missing or unreliable landmarks produce None for the corresponding
    angle. Raw canonical observations are not modified.
    """

    if not 0.0 <= confidence_threshold <= 1.0:
        raise ValueError(
            "confidence_threshold must be between 0 and 1"
        )

    output_frames: list[JointAngleFrame] = []

    for frame in sequence.frames:
        angles: dict[str, float | None] = {}

        for angle_name, landmark_names in (
            JOINT_ANGLE_DEFINITIONS.items()
        ):
            observations = [
                frame.keypoints[name]
                for name in landmark_names
            ]

            points = [
                _reliable_point(
                    observation,
                    confidence_threshold,
                )
                for observation in observations
            ]

            if any(point is None for point in points):
                angles[angle_name] = None
                continue

            point_a, vertex, point_c = points

            angles[angle_name] = calculate_angle_degrees(
                point_a,
                vertex,
                point_c,
            )

        output_frames.append(
            JointAngleFrame(
                frame_index=frame.frame_index,
                timestamp_ms=frame.timestamp_ms,
                angles_degrees=angles,
            )
        )

    return JointAngleSequence(
        frames=tuple(output_frames),
        fps=sequence.fps,
    )