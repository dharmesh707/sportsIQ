
import pytest

from app.ml.features.temporal import extract_temporal_features
from app.ml.pose.sequence import (
    ArmPose,
    LandmarkSample,
    PoseFrame,
    PoseSequence,
)


def _landmark(
    x: float,
    y: float,
    visibility: float = 0.9,
) -> LandmarkSample:
    return LandmarkSample(True, x, y, 0.0, visibility, 0.9)


def _frame(
    timestamp: int,
    wrist_x: float,
    angle: float = 90.0,
) -> PoseFrame:
    shoulder = _landmark(0.4, 0.4)
    elbow = _landmark(0.5, 0.5)
    wrist = _landmark(wrist_x, 0.5)

    arm = ArmPose(shoulder, elbow, wrist, angle)

    missing = ArmPose(
        LandmarkSample(False),
        LandmarkSample(False),
        LandmarkSample(False),
        None,
    )

    return PoseFrame(timestamp // 33, timestamp, missing, arm)


def _sequence(*frames: PoseFrame) -> PoseSequence:
    return PoseSequence(tuple(frames), 30.0, "right")


def test_constant_pose_has_zero_displacement_and_velocity_after_first_frame():
    features = extract_temporal_features(
        _sequence(
            _frame(0, 0.6),
            _frame(100, 0.6),
        )
    )

    assert features.frames[0].wrist_velocity_normalized_per_second is None
    assert features.frames[1].wrist_displacement_normalized == 0.0
    assert features.frames[1].wrist_velocity_normalized_per_second == 0.0


def test_moving_wrist_uses_elapsed_time():
    features = extract_temporal_features(
        _sequence(
            _frame(0, 0.6),
            _frame(200, 0.8),
        )
    )

    assert features.frames[1].wrist_displacement_normalized == pytest.approx(0.2)
    assert (
        features.frames[1].wrist_velocity_normalized_per_second
        == pytest.approx(1.0)
    )


def test_missing_racket_landmark_does_not_interpolate_features():
    missing = ArmPose(
        LandmarkSample(False),
        LandmarkSample(False),
        LandmarkSample(False),
        None,
    )

    features = extract_temporal_features(
        _sequence(
            _frame(0, 0.6),
            PoseFrame(1, 100, missing, missing),
        )
    )

    assert features.frames[1].wrist_x is None
    assert features.frames[1].wrist_velocity_normalized_per_second is None
    assert features.frames[1].wrist_displacement_normalized is None


def test_non_positive_timestamp_interval_does_not_produce_velocity():
    features = extract_temporal_features(
        _sequence(
            _frame(100, 0.6),
            _frame(100, 0.8),
        )
    )

    assert features.frames[1].wrist_velocity_normalized_per_second is None


def test_unreliable_quality_is_carried_into_features():
    features = extract_temporal_features(
        _sequence(
            _frame(0, 0.6, angle=90.0),
        ),
        0.95,
    )

    assert features.frames[0].quality_status == "unreliable"
    assert features.frames[0].racket_arm_quality_status == "unreliable"


def test_wrist_derivative_does_not_bridge_missing_pose_frame():
    missing = ArmPose(
        LandmarkSample(False),
        LandmarkSample(False),
        LandmarkSample(False),
        None,
    )

    sequence = _sequence(
        _frame(0, 0.4),
        PoseFrame(1, 100, missing, missing),
        _frame(200, 0.8),
    )

    features = extract_temporal_features(sequence)

    assert features.frames[1].wrist_velocity_normalized_per_second is None
    assert features.frames[2].wrist_displacement_normalized is None
    assert features.frames[2].wrist_velocity_normalized_per_second is None


def test_low_confidence_racket_arm_does_not_produce_velocity():
    low_confidence_arm = ArmPose(
        _landmark(0.4, 0.4, visibility=0.2),
        _landmark(0.5, 0.5, visibility=0.2),
        _landmark(0.6, 0.5, visibility=0.2),
        90.0,
    )

    reliable_arm = ArmPose(
        _landmark(0.4, 0.4),
        _landmark(0.5, 0.5),
        _landmark(0.8, 0.5),
        90.0,
    )

    missing_arm = ArmPose(
        LandmarkSample(False),
        LandmarkSample(False),
        LandmarkSample(False),
        None,
    )

    sequence = _sequence(
        PoseFrame(0, 0, missing_arm, low_confidence_arm),
        PoseFrame(1, 100, missing_arm, reliable_arm),
    )

    features = extract_temporal_features(sequence)

    assert features.frames[0].racket_arm_quality_status == "unreliable"
    assert features.frames[1].racket_arm_quality_status == "reliable"

    # A low-confidence observation should not be used as a reliable
    # starting point for a velocity calculation.
    assert features.frames[1].wrist_velocity_normalized_per_second is None
