"""Preprocess canonical full-body pose sequences into ML-ready features."""

from __future__ import annotations

import math
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from app.ml.pose.canonical import (
    CANONICAL_KEYPOINT_NAMES,
    CanonicalPoseSequence,
)
from app.ml.pose.canonical import FramePoseObservation


@dataclass(frozen=True)
class FullBodyKeypointFeature:
    """Image-space and body-relative features for one keypoint."""

    image_x_norm: float | None
    image_y_norm: float | None
    z_native: float | None

    body_relative_x: float | None
    body_relative_y: float | None

    visibility: float | None
    presence: float | None
    confidence: float | None

    valid: bool


@dataclass(frozen=True)
class FullBodyFeatureFrame:
    """Preprocessed full-body features for one source video frame."""

    frame_index: int
    timestamp_ms: int
    player_presence: str

    keypoints: Mapping[str, FullBodyKeypointFeature]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "keypoints",
            MappingProxyType(dict(self.keypoints)),
        )


@dataclass(frozen=True)
class FullBodyFeatureSequence:
    """Preprocessed features corresponding to a canonical pose sequence."""

    frames: tuple[FullBodyFeatureFrame, ...]
    fps: float | None

    feature_schema: str = "sportsiq.full_body_features"
    feature_version: str = "1.0"


def _is_reliable(
    observation,
    confidence_threshold: float,
) -> bool:
    """Determine whether a raw keypoint is reliable enough to use."""

    if not observation.present:
        return False

    for value in (
        observation.visibility,
        observation.presence,
        observation.confidence,
    ):
        if value is not None and value < confidence_threshold:
            return False

    return (
        observation.x_norm is not None
        and observation.y_norm is not None
        and math.isfinite(observation.x_norm)
        and math.isfinite(observation.y_norm)
    )


def _midpoint(
    first,
    second,
) -> tuple[float, float] | None:
    """Return the midpoint of two reliable keypoints."""

    if not first.present or not second.present:
        return None

    if (
        first.x_norm is None
        or first.y_norm is None
        or second.x_norm is None
        or second.y_norm is None
    ):
        return None

    return (
        (first.x_norm + second.x_norm) / 2.0,
        (first.y_norm + second.y_norm) / 2.0,
    )


def _body_reference(
    frame: FramePoseObservation,
    confidence_threshold: float,
) -> tuple[float, float, float] | None:
    """
    Calculate the body-relative reference.

    Origin:
        Midpoint between the shoulders.

    Scale:
        Distance between the shoulder midpoint and hip midpoint.

    The reference is unavailable when the required landmarks are missing
    or unreliable.
    """

    keypoints = frame.keypoints

    required_names = (
        "left_shoulder",
        "right_shoulder",
        "left_hip",
        "right_hip",
    )

    if any(
        not _is_reliable(
            keypoints[name],
            confidence_threshold,
        )
        for name in required_names
    ):
        return None

    shoulder_center = _midpoint(
        keypoints["left_shoulder"],
        keypoints["right_shoulder"],
    )

    hip_center = _midpoint(
        keypoints["left_hip"],
        keypoints["right_hip"],
    )

    if shoulder_center is None or hip_center is None:
        return None

    origin_x, origin_y = shoulder_center
    hip_x, hip_y = hip_center

    torso_scale = math.sqrt(
        (origin_x - hip_x) ** 2
        + (origin_y - hip_y) ** 2
    )

    if not math.isfinite(torso_scale) or torso_scale <= 1e-8:
        return None

    return origin_x, origin_y, torso_scale


def preprocess_full_body_sequence(
    sequence: CanonicalPoseSequence,
    *,
    confidence_threshold: float = 0.5,
) -> FullBodyFeatureSequence:
    """
    Convert a canonical sequence into body-relative ML features.

    Raw image-space coordinates and estimator-native z values are retained.
    Missing or unreliable landmarks are marked invalid.

    Body-relative coordinates use the shoulder midpoint as the origin
    and shoulder-to-hip center distance as the scale.
    """

    if not 0.0 <= confidence_threshold <= 1.0:
        raise ValueError(
            "confidence_threshold must be between 0 and 1"
        )

    output_frames: list[FullBodyFeatureFrame] = []

    for frame in sequence.frames:
        body_reference = _body_reference(
            frame,
            confidence_threshold,
        )

        if body_reference is None:
            origin_x = None
            origin_y = None
            torso_scale = None
        else:
            origin_x, origin_y, torso_scale = body_reference

        feature_keypoints: dict[str, FullBodyKeypointFeature] = {}

        for name in CANONICAL_KEYPOINT_NAMES:
            observation = frame.keypoints[name]

            valid = _is_reliable(
                observation,
                confidence_threshold,
            )

            image_x = observation.x_norm if observation.present else None
            image_y = observation.y_norm if observation.present else None

            relative_x = None
            relative_y = None

            if (
                valid
                and origin_x is not None
                and origin_y is not None
                and torso_scale is not None
                and image_x is not None
                and image_y is not None
            ):
                relative_x = (image_x - origin_x) / torso_scale
                relative_y = (image_y - origin_y) / torso_scale

            feature_keypoints[name] = FullBodyKeypointFeature(
                image_x_norm=image_x,
                image_y_norm=image_y,
                z_native=(
                    observation.z_native
                    if observation.present
                    else None
                ),
                body_relative_x=relative_x,
                body_relative_y=relative_y,
                visibility=observation.visibility,
                presence=observation.presence,
                confidence=observation.confidence,
                valid=valid,
            )

        output_frames.append(
            FullBodyFeatureFrame(
                frame_index=frame.frame_index,
                timestamp_ms=frame.timestamp_ms,
                player_presence=frame.player_presence,
                keypoints=feature_keypoints,
            )
        )

    return FullBodyFeatureSequence(
        frames=tuple(output_frames),
        fps=sequence.fps,
    )