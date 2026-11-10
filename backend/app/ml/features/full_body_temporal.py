from __future__ import annotations
from dataclasses import dataclass
from math import hypot, isfinite
from typing import Optional

from app.ml.features.full_body import FullBodyFeatureSequence
from app.ml.features.joint_angles import JointAngleSequence

@dataclass(frozen=True)
class TemporalFeatureFrame:
    """
    Temporal features for one frame.

    Feature values are keyed by stable names:
      - keypoint velocity: <keypoint>_velocity
      - keypoint acceleration: <keypoint>_acceleration
      - angle velocity: <angle_name>_angular_velocity

    Missing or unreliable calculations are represented as None.
    """

    frame_index: int
    timestamp_ms: float
    features: dict[str, Optional[float]]

@dataclass(frozen=True)
class TemporalFeatureSequence:
    frames: list[TemporalFeatureFrame]
    fps: float
    feature_schema: str
    feature_version: str

def _finite(value: Optional[float]) -> bool:
    return value is not None and isfinite(value)

def _valid_keypoint_position(keypoint) -> bool:
    """
    A point must be marked valid and have finite body-relative coordinates.
    """
    if keypoint is None:
        return False

    if not getattr(keypoint, "valid", False):
        return False

    x = getattr(keypoint, "body_relative_x", None)
    y = getattr(keypoint, "body_relative_y", None)

    return _finite(x) and _finite(y)

def _position_distance(point_a, point_b) -> Optional[float]:
    """
    Euclidean displacement between two body-relative keypoint positions.
    """
    if not _valid_keypoint_position(point_a):
        return None

    if not _valid_keypoint_position(point_b):
        return None

    dx = point_b.body_relative_x - point_a.body_relative_x
    dy = point_b.body_relative_y - point_a.body_relative_y

    distance = hypot(dx, dy)

    return distance if isfinite(distance) else None

def _time_delta_seconds(timestamp_a: float, timestamp_b: float) -> Optional[float]:
    """
    Return positive elapsed time between timestamps.

    Non-positive or invalid time deltas are rejected to prevent invalid
    velocity and acceleration calculations.
    """
    if not _finite(timestamp_a) or not _finite(timestamp_b):
        return None

    delta = (timestamp_b - timestamp_a) / 1000.0

    if delta <= 0:
        return None

    return delta

def _calculate_velocity(
    point_a,
    point_b,
    timestamp_a: float,
    timestamp_b: float,
) -> Optional[float]:
    """
    Calculate scalar displacement speed in body-relative units per second.
    """
    distance = _position_distance(point_a, point_b)

    if distance is None:
        return None

    delta_time = _time_delta_seconds(timestamp_a, timestamp_b)

    if delta_time is None:
        return None

    velocity = distance / delta_time

    return velocity if isfinite(velocity) else None

def _calculate_acceleration(
    velocity_a: Optional[float],
    velocity_b: Optional[float],
    timestamp_a: float,
    timestamp_b: float,
) -> Optional[float]:
    """
    Calculate change in scalar speed per second.

    This is speed acceleration, not a signed x/y acceleration vector.
    """
    if not _finite(velocity_a) or not _finite(velocity_b):
        return None

    delta_time = _time_delta_seconds(timestamp_a, timestamp_b)

    if delta_time is None:
        return None

    acceleration = (velocity_b - velocity_a) / delta_time

    return acceleration if isfinite(acceleration) else None

def _calculate_angular_velocity(
    angle_a: Optional[float],
    angle_b: Optional[float],
    timestamp_a: float,
    timestamp_b: float,
) -> Optional[float]:
    """
    Calculate angular velocity in degrees per second.

    Angles currently use unsigned 2D joint angles in [0, 180].
    Therefore, this is a change in angle magnitude, not a signed rotation.
    """
    if not _finite(angle_a) or not _finite(angle_b):
        return None

    delta_time = _time_delta_seconds(timestamp_a, timestamp_b)

    if delta_time is None:
        return None

    angular_velocity = (angle_b - angle_a) / delta_time

    return angular_velocity if isfinite(angular_velocity) else None

def extract_full_body_temporal_features(
    position_sequence: FullBodyFeatureSequence,
    angle_sequence: JointAngleSequence,
) -> TemporalFeatureSequence:
    """
    Extract temporal movement features from aligned full-body positions
    and joint-angle sequences.

    Requirements:
      - Position and angle sequences must have the same number of frames.
      - Frames must correspond in order.
      - Timestamps are used for derivatives rather than assuming a fixed FPS.

    Returns one TemporalFeatureFrame per input frame.
    """
    position_frames = position_sequence.frames
    angle_frames = angle_sequence.frames

    if len(position_frames) != len(angle_frames):
        raise ValueError(
            "Position and angle sequences must contain the same number "
            f"of frames. Got {len(position_frames)} and "
            f"{len(angle_frames)}."
        )
    if not position_frames:
        return TemporalFeatureSequence(
            frames=[],
            fps=position_sequence.fps,
            feature_schema="full_body_temporal",
            feature_version="1.0.0",
        )

    for position_frame, angle_frame in zip(position_frames, angle_frames):
        if position_frame.frame_index != angle_frame.frame_index:
            raise ValueError(
                "Position and angle frame indices must align. "
                f"Got {position_frame.frame_index} and "
                f"{angle_frame.frame_index}."
            )

    # Preserve the keypoint and angle names present in the input sequences.
    keypoint_names = sorted(
        {
            keypoint_name
            for frame in position_frames
            for keypoint_name in frame.keypoints
        }
    )

    angle_names = sorted(
        {
            angle_name
            for frame in angle_frames
            for angle_name in frame.angles_degrees
        }
    )

    # First calculate velocity for each frame transition.
    #
    # A transition at index i describes movement from frame i to i + 1.
    # We store it at i + 1 so the derived feature is associated with
    # the destination frame.
    velocity_by_frame: list[dict[str, Optional[float]]] = [
        {} for _ in position_frames
    ]

    angular_velocity_by_frame: list[dict[str, Optional[float]]] = [
        {} for _ in angle_frames
    ]

    for frame_index in range(1, len(position_frames)):
        previous_position_frame = position_frames[frame_index - 1]
        current_position_frame = position_frames[frame_index]

        previous_angle_frame = angle_frames[frame_index - 1]
        current_angle_frame = angle_frames[frame_index]

        previous_timestamp = previous_position_frame.timestamp_ms
        current_timestamp = current_position_frame.timestamp_ms

        for keypoint_name in keypoint_names:
            previous_point = previous_position_frame.keypoints.get(
                keypoint_name
            )
            current_point = current_position_frame.keypoints.get(
                keypoint_name
            )

            velocity_by_frame[frame_index][
                f"{keypoint_name}_velocity"
            ] = _calculate_velocity(
                previous_point,
                current_point,
                previous_timestamp,
                current_timestamp,
            )

        for angle_name in angle_names:
            previous_angle = previous_angle_frame.angles_degrees.get(
                angle_name
            )
            current_angle = current_angle_frame.angles_degrees.get(
                angle_name
            )

            angular_velocity_by_frame[frame_index][
                f"{angle_name}_angular_velocity"
            ] = _calculate_angular_velocity(
                previous_angle,
                current_angle,
                previous_timestamp,
                current_timestamp,
            )

    # Calculate acceleration from consecutive valid velocities.
    acceleration_by_frame: list[dict[str, Optional[float]]] = [
        {} for _ in position_frames
    ]

    for frame_index in range(2, len(position_frames)):
        previous_timestamp = position_frames[frame_index - 1].timestamp_ms
        current_timestamp = position_frames[frame_index].timestamp_ms

        for keypoint_name in keypoint_names:
            feature_name = f"{keypoint_name}_velocity"

            previous_velocity = velocity_by_frame[frame_index - 1].get(
                feature_name
            )
            current_velocity = velocity_by_frame[frame_index].get(
                feature_name
            )

            acceleration_by_frame[frame_index][
                f"{keypoint_name}_acceleration"
            ] = _calculate_acceleration(
                previous_velocity,
                current_velocity,
                previous_timestamp,
                current_timestamp,
            )

    # Combine all features into one frame-level representation.
    temporal_frames: list[TemporalFeatureFrame] = []

    for frame_index, position_frame in enumerate(position_frames):
        features: dict[str, Optional[float]] = {}

        # Include position features as well as temporal derivatives.
        for keypoint_name in keypoint_names:
            keypoint = position_frame.keypoints.get(keypoint_name)

            if _valid_keypoint_position(keypoint):
                features[f"{keypoint_name}_body_relative_x"] = (
                    keypoint.body_relative_x
                )
                features[f"{keypoint_name}_body_relative_y"] = (
                    keypoint.body_relative_y
                )
            else:
                features[f"{keypoint_name}_body_relative_x"] = None
                features[f"{keypoint_name}_body_relative_y"] = None

            features[f"{keypoint_name}_velocity"] = (
                velocity_by_frame[frame_index].get(
                    f"{keypoint_name}_velocity"
                )
            )

            features[f"{keypoint_name}_acceleration"] = (
                acceleration_by_frame[frame_index].get(
                    f"{keypoint_name}_acceleration"
                )
            )

        # Include joint angles and their temporal derivatives.
        angle_frame = angle_frames[frame_index]

        for angle_name in angle_names:
            angle_value = angle_frame.angles_degrees.get(angle_name)

            features[f"{angle_name}_angle_degrees"] = (
                angle_value if _finite(angle_value) else None
            )

            features[f"{angle_name}_angular_velocity"] = (
                angular_velocity_by_frame[frame_index].get(
                    f"{angle_name}_angular_velocity"
                )
            )

        temporal_frames.append(
            TemporalFeatureFrame(
                frame_index=position_frame.frame_index,
                timestamp_ms=position_frame.timestamp_ms,
                features=features,
            )
        )

    return TemporalFeatureSequence(
        frames=temporal_frames,
        fps=position_sequence.fps,
        feature_schema="full_body_temporal",
        feature_version="1.0.0",
    )
