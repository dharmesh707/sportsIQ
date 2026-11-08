"""Temporal, diagnostic-only features for badminton pose sequences."""

from __future__ import annotations

import math
from dataclasses import dataclass

from app.ml.pose.quality import (
    DEFAULT_CONFIDENCE_THRESHOLD,
    assess_arm_roles,
    assess_frame_quality,
)
from app.ml.pose.sequence import ArmPose, PoseSequence, RacketSide


@dataclass(frozen=True)
class TemporalFeatureFrame:
    """Features for one frame; unavailable derivatives remain None."""

    frame_index: int
    timestamp_ms: int
    racket_side: RacketSide
    quality_status: str
    quality_reasons: tuple[str, ...]
    racket_arm_quality_status: str
    racket_arm_quality_reasons: tuple[str, ...]
    shoulder_x: float | None
    shoulder_y: float | None
    shoulder_z: float | None
    elbow_x: float | None
    elbow_y: float | None
    elbow_z: float | None
    wrist_x: float | None
    wrist_y: float | None
    wrist_z: float | None
    shoulder_visibility: float | None
    shoulder_presence: float | None
    elbow_visibility: float | None
    elbow_presence: float | None
    wrist_visibility: float | None
    wrist_presence: float | None
    elbow_angle_2d_degrees: float | None
    elbow_angle_3d_degrees: float | None
    shoulder_elevation_degrees: float | None
    wrist_velocity_normalized_per_second: float | None
    elbow_angular_velocity_degrees_per_second: float | None
    wrist_displacement_normalized: float | None


@dataclass(frozen=True)
class TemporalFeatureSequence:
    """Ordered temporal features suitable for later model training."""

    frames: tuple[TemporalFeatureFrame, ...]
    racket_side: RacketSide


def _finite(value: float | None) -> bool:
    return value is not None and math.isfinite(value)


def _position(
    arm: ArmPose,
    joint: str,
) -> tuple[float, float] | None:
    landmark = getattr(arm, joint)

    if (
        not landmark.present
        or not _finite(landmark.x)
        or not _finite(landmark.y)
    ):
        return None

    return landmark.x, landmark.y


def _coordinate(
    arm: ArmPose | None,
    joint: str,
    axis: str,
) -> float | None:
    if arm is None:
        return None

    landmark = getattr(arm, joint)

    if not landmark.present:
        return None

    value = getattr(landmark, axis)
    return value if _finite(value) else None


def _shoulder_elevation(arm: ArmPose) -> float | None:
    shoulder = _position(arm, "shoulder")
    wrist = _position(arm, "wrist")

    if shoulder is None or wrist is None:
        return None

    dx = wrist[0] - shoulder[0]
    dy = wrist[1] - shoulder[1]

    if dx == 0 and dy == 0:
        return None

    return math.degrees(math.atan2(-dy, dx))


def _time_delta_seconds(
    previous_timestamp_ms: int,
    timestamp_ms: int,
) -> float | None:
    delta_ms = timestamp_ms - previous_timestamp_ms

    if delta_ms <= 0:
        return None

    return delta_ms / 1000.0


def _distance(
    first: tuple[float, float] | None,
    last: tuple[float, float] | None,
) -> float | None:
    if first is None or last is None:
        return None

    return math.hypot(
        last[0] - first[0],
        last[1] - first[1],
    )


def _signed_angle_delta(
    previous: float | None,
    current: float | None,
) -> float | None:
    if not _finite(previous) or not _finite(current):
        return None

    return current - previous


def extract_temporal_features(
    sequence: PoseSequence,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> TemporalFeatureSequence:
    """Extract nullable temporal features from the configured racket arm."""

    if not 0.0 <= confidence_threshold <= 1.0:
        raise ValueError(
            "confidence_threshold must be between 0 and 1"
        )

    previous_timestamp: int | None = None
    previous_wrist: tuple[float, float] | None = None
    previous_angle: float | None = None
    previous_racket_arm_reliable = False

    feature_frames: list[TemporalFeatureFrame] = []

    for pose_frame in sequence.frames:
        quality = assess_frame_quality(
            pose_frame,
            confidence_threshold,
        )

        racket_quality, _ = assess_arm_roles(
            pose_frame,
            sequence.racket_side,
            confidence_threshold,
        )

        arm = (
            pose_frame.left
            if sequence.racket_side == "left"
            else pose_frame.right
            if sequence.racket_side == "right"
            else None
        )

        wrist = _position(arm, "wrist") if arm is not None else None
        shoulder = (
            _position(arm, "shoulder")
            if arm is not None
            else None
        )
        elbow = _position(arm, "elbow") if arm is not None else None

        angle_2d = (
            _diagnostic_2d_angle(arm)
            if arm is not None
            else None
        )

        angle_3d = (
            arm.elbow_angle_degrees
            if arm is not None
            else None
        )

        current_racket_arm_reliable = (
            racket_quality.status == "reliable"
        )

        dt = (
            _time_delta_seconds(
                previous_timestamp,
                pose_frame.timestamp_ms,
            )
            if previous_timestamp is not None
            else None
        )

        # Derivatives require reliable observations at both endpoints.
        derivative_usable = (
            previous_racket_arm_reliable
            and current_racket_arm_reliable
            and dt is not None
        )

        displacement = (
            _distance(previous_wrist, wrist)
            if derivative_usable
            else None
        )

        wrist_velocity = (
            displacement / dt
            if displacement is not None and dt is not None
            else None
        )

        angle_delta = (
            _signed_angle_delta(
                previous_angle,
                angle_2d,
            )
            if derivative_usable
            else None
        )

        angular_velocity = (
            angle_delta / dt
            if angle_delta is not None and dt is not None
            else None
        )

        feature_frames.append(
            TemporalFeatureFrame(
                frame_index=pose_frame.frame_index,
                timestamp_ms=pose_frame.timestamp_ms,
                racket_side=sequence.racket_side,
                quality_status=(
                    "reliable"
                    if quality.reliable
                    else "unreliable"
                ),
                quality_reasons=quality.reasons,
                racket_arm_quality_status=racket_quality.status,
                racket_arm_quality_reasons=racket_quality.reasons,
                shoulder_x=shoulder[0] if shoulder else None,
                shoulder_y=shoulder[1] if shoulder else None,
                shoulder_z=_coordinate(
                    arm,
                    "shoulder",
                    "z",
                ),
                elbow_x=elbow[0] if elbow else None,
                elbow_y=elbow[1] if elbow else None,
                elbow_z=_coordinate(
                    arm,
                    "elbow",
                    "z",
                ),
                wrist_x=wrist[0] if wrist else None,
                wrist_y=wrist[1] if wrist else None,
                wrist_z=_coordinate(
                    arm,
                    "wrist",
                    "z",
                ),
                shoulder_visibility=(
                    arm.shoulder.visibility
                    if arm
                    else None
                ),
                shoulder_presence=(
                    arm.shoulder.presence
                    if arm
                    else None
                ),
                elbow_visibility=(
                    arm.elbow.visibility
                    if arm
                    else None
                ),
                elbow_presence=(
                    arm.elbow.presence
                    if arm
                    else None
                ),
                wrist_visibility=(
                    arm.wrist.visibility
                    if arm
                    else None
                ),
                wrist_presence=(
                    arm.wrist.presence
                    if arm
                    else None
                ),
                elbow_angle_2d_degrees=angle_2d,
                elbow_angle_3d_degrees=angle_3d,
                shoulder_elevation_degrees=(
                    _shoulder_elevation(arm)
                    if arm
                    else None
                ),
                wrist_velocity_normalized_per_second=(
                    wrist_velocity
                ),
                elbow_angular_velocity_degrees_per_second=(
                    angular_velocity
                ),
                wrist_displacement_normalized=displacement,
            )
        )

        # Update state after extracting the current frame.
        previous_timestamp = pose_frame.timestamp_ms
        previous_wrist = wrist
        previous_angle = angle_2d
        previous_racket_arm_reliable = (
            current_racket_arm_reliable
        )

    return TemporalFeatureSequence(
        tuple(feature_frames),
        sequence.racket_side,
    )


def _diagnostic_2d_angle(
    arm: ArmPose,
) -> float | None:
    shoulder = _position(arm, "shoulder")
    elbow = _position(arm, "elbow")
    wrist = _position(arm, "wrist")

    if shoulder is None or elbow is None or wrist is None:
        return None

    first = (
        shoulder[0] - elbow[0],
        shoulder[1] - elbow[1],
    )

    last = (
        wrist[0] - elbow[0],
        wrist[1] - elbow[1],
    )

    denominator = (
        math.hypot(*first)
        * math.hypot(*last)
    )

    if denominator <= 0 or not math.isfinite(denominator):
        return None

    cosine = (
        first[0] * last[0]
        + first[1] * last[1]
    ) / denominator

    if not math.isfinite(cosine):
        return None

    return math.degrees(
        math.acos(
            max(-1.0, min(1.0, cosine))
        )
    )