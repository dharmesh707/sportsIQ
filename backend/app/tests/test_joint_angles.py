"""Tests for full-body joint-angle extraction."""

import pytest

from app.ml.pose.canonical import (
    CANONICAL_KEYPOINT_NAMES,
    CanonicalPoseSequence,
    FramePoseObservation,
    KeypointObservation,
)
from app.ml.features.joint_angles import (
    JOINT_ANGLE_DEFINITIONS,
    calculate_angle_degrees,
    extract_joint_angles,
)


def make_keypoint(
    x: float,
    y: float,
    *,
    visibility: float = 0.9,
) -> KeypointObservation:
    return KeypointObservation(
        present=True,
        x_norm=x,
        y_norm=y,
        visibility=visibility,
        presence=0.9,
        confidence=0.9,
    )


def make_frame(
    frame_index: int = 0,
    overrides: dict[str, KeypointObservation] | None = None,
) -> FramePoseObservation:
    keypoints = {
        name: KeypointObservation.missing()
        for name in CANONICAL_KEYPOINT_NAMES
    }

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


def test_calculates_right_angle():
    angle = calculate_angle_degrees(
        point_a=(1.0, 0.0),
        vertex=(0.0, 0.0),
        point_c=(0.0, 1.0),
    )

    assert angle == pytest.approx(90.0)


def test_calculates_straight_angle():
    angle = calculate_angle_degrees(
        point_a=(-1.0, 0.0),
        vertex=(0.0, 0.0),
        point_c=(1.0, 0.0),
    )

    assert angle == pytest.approx(180.0)


def test_zero_length_vector_returns_none():
    angle = calculate_angle_degrees(
        point_a=(0.0, 0.0),
        vertex=(0.0, 0.0),
        point_c=(1.0, 0.0),
    )

    assert angle is None


def test_extracts_elbow_angle():
    frame = make_frame(
        overrides={
            "left_shoulder": make_keypoint(0.0, 0.0),
            "left_elbow": make_keypoint(1.0, 0.0),
            "left_wrist": make_keypoint(1.0, 1.0),
        }
    )

    result = extract_joint_angles(make_sequence(frame))

    assert (
        result.frames[0].angles_degrees["left_elbow"]
        == pytest.approx(90.0)
    )


def test_missing_landmark_returns_none_for_angle():
    frame = make_frame(
        overrides={
            "left_shoulder": make_keypoint(0.0, 0.0),
            "left_elbow": make_keypoint(1.0, 0.0),
            # left_wrist intentionally missing
        }
    )

    result = extract_joint_angles(make_sequence(frame))

    assert result.frames[0].angles_degrees["left_elbow"] is None


def test_low_visibility_landmark_returns_none_for_angle():
    frame = make_frame(
        overrides={
            "left_shoulder": make_keypoint(0.0, 0.0),
            "left_elbow": make_keypoint(
                1.0,
                0.0,
                visibility=0.2,
            ),
            "left_wrist": make_keypoint(1.0, 1.0),
        }
    )

    result = extract_joint_angles(
        make_sequence(frame),
        confidence_threshold=0.5,
    )

    assert result.frames[0].angles_degrees["left_elbow"] is None


def test_all_defined_angle_names_are_returned():
    frame = make_frame()

    result = extract_joint_angles(make_sequence(frame))

    assert set(result.frames[0].angles_degrees) == set(
        JOINT_ANGLE_DEFINITIONS
    )


def test_preserves_frame_metadata():
    frame = make_frame(frame_index=7)

    result = extract_joint_angles(make_sequence(frame))

    assert result.frames[0].frame_index == 7
    assert result.frames[0].timestamp_ms == 231
    assert result.fps == pytest.approx(30.0)


def test_rejects_invalid_confidence_threshold():
    sequence = make_sequence(make_frame())

    with pytest.raises(ValueError):
        extract_joint_angles(
            sequence,
            confidence_threshold=1.5,
        )