"""Tests for full-body feature preprocessing."""

import pytest

from app.ml.pose.canonical import (
    CANONICAL_KEYPOINT_NAMES,
    CanonicalPoseSequence,
    FramePoseObservation,
    KeypointObservation,
)
from app.ml.features.full_body import preprocess_full_body_sequence


def make_keypoint(
    x: float,
    y: float,
    *,
    visibility: float = 0.9,
    presence: float = 0.9,
    confidence: float = 0.9,
    z: float = 0.1,
) -> KeypointObservation:
    return KeypointObservation(
        present=True,
        x_norm=x,
        y_norm=y,
        z_native=z,
        visibility=visibility,
        presence=presence,
        confidence=confidence,
    )


def make_frame(
    frame_index: int = 0,
    *,
    overrides: dict[str, KeypointObservation] | None = None,
) -> FramePoseObservation:
    keypoints = {
        name: KeypointObservation.missing()
        for name in CANONICAL_KEYPOINT_NAMES
    }

    # Reliable torso anchors.
    keypoints.update(
        {
            "left_shoulder": make_keypoint(0.4, 0.3),
            "right_shoulder": make_keypoint(0.6, 0.3),
            "left_hip": make_keypoint(0.45, 0.6),
            "right_hip": make_keypoint(0.55, 0.6),
        }
    )

    if overrides:
        keypoints.update(overrides)

    return FramePoseObservation(
        frame_index=frame_index,
        timestamp_ms=frame_index * 33,
        width_px=640,
        height_px=480,
        keypoints=keypoints,
        player_presence="PLAYER_PRESENT",
    )


def make_sequence(
    frame: FramePoseObservation,
) -> CanonicalPoseSequence:
    return CanonicalPoseSequence(
        frames=(frame,),
        estimator_name="test-estimator",
        estimator_version="1.0",
        model_name="test-model",
        fps=30.0,
    )


def test_calculates_body_relative_coordinates():
    frame = make_frame(
        overrides={
            "nose": make_keypoint(0.5, 0.0),
        }
    )

    result = preprocess_full_body_sequence(
        make_sequence(frame)
    )

    nose = result.frames[0].keypoints["nose"]

    assert nose.valid is True
    assert nose.image_x_norm == pytest.approx(0.5)
    assert nose.image_y_norm == pytest.approx(0.0)

    # Shoulder midpoint is (0.5, 0.3).
    # Shoulder-to-hip center distance is 0.3.
    assert nose.body_relative_x == pytest.approx(0.0)
    assert nose.body_relative_y == pytest.approx(-1.0)


def test_preserves_image_coordinates_when_body_anchor_is_missing():
    frame = make_frame(
        overrides={
            "left_hip": KeypointObservation.missing(),
        }
    )

    result = preprocess_full_body_sequence(
        make_sequence(frame)
    )

    shoulder = result.frames[0].keypoints["left_shoulder"]

    assert shoulder.valid is True
    assert shoulder.image_x_norm == pytest.approx(0.4)
    assert shoulder.image_y_norm == pytest.approx(0.3)

    # Body-relative coordinates require all torso anchors.
    assert shoulder.body_relative_x is None
    assert shoulder.body_relative_y is None


def test_missing_keypoint_is_not_fabricated():
    frame = make_frame()

    result = preprocess_full_body_sequence(
        make_sequence(frame)
    )

    wrist = result.frames[0].keypoints["left_wrist"]

    assert wrist.valid is False
    assert wrist.image_x_norm is None
    assert wrist.image_y_norm is None
    assert wrist.body_relative_x is None
    assert wrist.body_relative_y is None


def test_low_confidence_anchor_invalidates_body_reference():
    frame = make_frame(
        overrides={
            "left_shoulder": make_keypoint(
                0.4,
                0.3,
                visibility=0.2,
            ),
        }
    )

    result = preprocess_full_body_sequence(
        make_sequence(frame)
    )

    nose = result.frames[0].keypoints["nose"]

    # The nose itself is reliable, but the body reference is not.
    assert nose.valid is False
    assert nose.body_relative_x is None
    assert nose.body_relative_y is None


def test_rejects_zero_length_torso_reference():
    frame = make_frame(
        overrides={
            "left_hip": make_keypoint(0.45, 0.3),
            "right_hip": make_keypoint(0.55, 0.3),
        }
    )

    result = preprocess_full_body_sequence(
        make_sequence(frame)
    )

    nose = result.frames[0].keypoints["nose"]

    assert nose.valid is False
    assert nose.body_relative_x is None
    assert nose.body_relative_y is None


def test_rejects_invalid_confidence_threshold():
    sequence = make_sequence(make_frame())

    with pytest.raises(ValueError):
        preprocess_full_body_sequence(
            sequence,
            confidence_threshold=1.5,
        )


def test_preserves_frame_metadata():
    frame = make_frame(frame_index=7)

    result = preprocess_full_body_sequence(
        make_sequence(frame)
    )

    output_frame = result.frames[0]

    assert output_frame.frame_index == 7
    assert output_frame.timestamp_ms == 231
    assert output_frame.player_presence == "PLAYER_PRESENT"
    assert result.fps == pytest.approx(30.0)