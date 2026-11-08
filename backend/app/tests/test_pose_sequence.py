from types import SimpleNamespace
import csv

from app.ml.pose.sequence import (
    ArmPose,
    LandmarkSample,
    PoseFrame,
    PoseSequence,
    _arm_pose,
    _timestamp_ms,
    _validate_fps,
    calculate_elbow_angle,
    safe_angle_degrees,
)
from app.ml.scripts.validate_pose_sequence import (
    angle_disagreement_warning,
    calculate_angle_disagreement,
    calculate_elbow_angle_2d,
    write_sequence_csv,
)


def _landmark(
    x: float,
    y: float,
    z: float = 0.0,
    visibility: float = 0.8,
    presence: float = 0.9,
):
    return SimpleNamespace(x=x, y=y, z=z, visibility=visibility, presence=presence)


def test_calculates_both_arm_angles_and_preserves_visibility():
    landmarks = [_landmark(0, 0) for _ in range(17)]
    landmarks[11] = _landmark(0, 1)
    landmarks[13] = _landmark(0, 0)
    landmarks[15] = _landmark(1, 0, visibility=0.7)
    landmarks[12] = _landmark(0, 1)
    landmarks[14] = _landmark(0, 0)
    landmarks[16] = _landmark(-1, 0, visibility=0.6)

    left = _arm_pose(landmarks, "left")
    right = _arm_pose(landmarks, "right")
    assert left.elbow_angle_degrees == 90.0
    assert right.elbow_angle_degrees == 90.0
    assert left.wrist.visibility == 0.7
    assert right.wrist.visibility == 0.6


def test_missing_landmark_returns_missing_and_no_angle():
    arm = _arm_pose([_landmark(0, 0)] * 14, "left")
    assert not arm.wrist.present
    assert arm.elbow_angle_degrees is None


def test_invalid_angles_return_none():
    assert safe_angle_degrees((0, 0, 0), (0, 0, 0), (1, 0, 0)) is None
    invalid = LandmarkSample(present=True, x=float("nan"), y=0.0, z=0.0)
    valid = LandmarkSample(present=True, x=1.0, y=0.0, z=0.0)
    assert calculate_elbow_angle(valid, valid, invalid) is None


def test_timestamps_are_monotonic_even_when_fps_rounds_to_same_value():
    timestamps = []
    previous = None
    for frame_index in range(5):
        previous = _timestamp_ms(frame_index, 1000.0, previous)
        timestamps.append(previous)
    assert timestamps == sorted(set(timestamps))


def test_invalid_fps_is_rejected():
    for fps in (0.0, -30.0, float("nan"), float("inf"), float("-inf")):
        try:
            _validate_fps(fps)
        except ValueError as error:
            assert "finite positive" in str(error)
        else:
            raise AssertionError(f"Expected invalid FPS to fail: {fps!r}")


def test_non_finite_or_out_of_range_confidence_is_none():
    landmarks = [_landmark(0, 0) for _ in range(17)]
    landmarks[11] = _landmark(0, 1, visibility=float("nan"), presence=float("inf"))
    landmarks[13] = _landmark(0, 0, visibility=-0.1, presence=1.1)
    landmarks[15] = _landmark(1, 0, visibility=0.7, presence=0.8)

    arm = _arm_pose(landmarks, "left")
    assert arm.shoulder.visibility is None
    assert arm.shoulder.presence is None
    assert arm.elbow.visibility is None
    assert arm.elbow.presence is None
    assert arm.wrist.visibility == 0.7
    assert arm.wrist.presence == 0.8


def test_timestamp_helper_requires_fps_and_strictly_increases():
    timestamps = [
        _timestamp_ms(frame_index, 29.97, previous)
        for frame_index, previous in enumerate([None, 33, 67, 100])
    ]
    assert timestamps == sorted(set(timestamps))
    try:
        _timestamp_ms(0, 0.0, None)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected timestamp generation to reject unavailable FPS")


def test_validator_preserves_missing_values_in_csv(tmp_path):
    valid = LandmarkSample(
        present=True,
        x=0.1,
        y=0.2,
        z=0.3,
        visibility=0.8,
        presence=0.9,
    )
    missing = LandmarkSample(present=False)
    left_shoulder = LandmarkSample(
        present=True,
        x=0.1,
        y=1.2,
        z=0.3,
        visibility=0.8,
        presence=0.9,
    )
    left_elbow = LandmarkSample(
        present=True,
        x=0.1,
        y=0.2,
        z=0.3,
        visibility=0.8,
        presence=0.9,
    )
    left_wrist = LandmarkSample(
        present=True,
        x=1.1,
        y=0.2,
        z=0.3,
        visibility=0.8,
        presence=0.9,
    )
    sequence = PoseSequence(
        frames=(
            PoseFrame(
                frame_index=0,
                timestamp_ms=0,
                left=ArmPose(left_shoulder, left_elbow, left_wrist, 120.0),
                right=ArmPose(valid, valid, missing, None),
            ),
        ),
        fps=30.0,
        racket_side="unknown",
    )
    output_path = tmp_path / "sequence.csv"
    write_sequence_csv(sequence, output_path)

    with output_path.open(newline="", encoding="utf-8") as file:
        row = next(csv.DictReader(file))
    assert row["left_elbow_angle_degrees"] == "120.0"
    assert row["left_elbow_angle_2d_degrees"] == "90.0"
    assert row["left_elbow_angle_disagreement_degrees"] == "30.0"
    assert row["left_elbow_angle_disagreement_warning"] == "False"
    assert row["frame_quality_status"] == "unreliable"
    assert "right_wrist_missing" in row["frame_quality_reasons"]
    assert row["racket_arm_quality_status"] == "unknown"
    assert row["racket_arm_quality_reasons"] == "racket_side_unknown"
    assert row["non_racket_arm_quality_status"] == "unknown"
    assert row["left_shoulder_x"] == "0.1"
    assert row["left_shoulder_y"] == "1.2"
    assert row["left_shoulder_z"] == "0.3"
    assert row["left_shoulder_visibility"] == "0.8"
    assert row["left_shoulder_presence"] == "0.9"
    assert row["right_elbow_angle_degrees"] == ""
    assert row["right_elbow_angle_2d_degrees"] == ""
    assert row["right_elbow_angle_disagreement_degrees"] == ""
    assert row["right_elbow_angle_disagreement_warning"] == "False"
    assert row["right_wrist_x"] == ""
    assert row["right_wrist_y"] == ""
    assert row["right_wrist_z"] == ""
    assert row["right_wrist_visibility"] == ""
    assert row["right_wrist_presence"] == ""


def test_calculates_valid_2d_angles_for_both_arms():
    landmark = LandmarkSample(present=True, x=0.0, y=0.0)
    left = ArmPose(
        shoulder=LandmarkSample(present=True, x=0.0, y=1.0),
        elbow=landmark,
        wrist=LandmarkSample(present=True, x=1.0, y=0.0),
        elbow_angle_degrees=90.0,
    )
    right = ArmPose(
        shoulder=LandmarkSample(present=True, x=0.0, y=1.0),
        elbow=landmark,
        wrist=LandmarkSample(present=True, x=-1.0, y=0.0),
        elbow_angle_degrees=90.0,
    )

    assert calculate_elbow_angle_2d(left) == 90.0
    assert calculate_elbow_angle_2d(right) == 90.0


def test_2d_angle_is_missing_when_a_landmark_is_missing():
    valid = LandmarkSample(present=True, x=0.0, y=0.0)
    missing = LandmarkSample(present=False)
    arm = ArmPose(valid, missing, valid, elbow_angle_degrees=None)

    assert calculate_elbow_angle_2d(arm) is None


def test_angle_disagreement_handles_small_and_large_values():
    assert calculate_angle_disagreement(100.0, 90.0) == 10.0
    assert angle_disagreement_warning(100.0, 69.0) is True
    assert angle_disagreement_warning(100.0, 90.0) is False


def test_angle_disagreement_warning_is_false_at_exact_threshold():
    assert calculate_angle_disagreement(120.0, 90.0) == 30.0
    assert angle_disagreement_warning(120.0, 90.0, 30.0) is False


def test_angle_disagreement_is_missing_when_an_angle_is_unavailable():
    assert calculate_angle_disagreement(None, 90.0) is None
    assert angle_disagreement_warning(None, 90.0) is False


def test_angle_disagreement_handles_both_arms_independently():
    left = calculate_angle_disagreement(120.0, 80.0)
    right = calculate_angle_disagreement(100.0, 90.0)

    assert left == 40.0
    assert right == 10.0
    assert angle_disagreement_warning(120.0, 80.0) is True
    assert angle_disagreement_warning(100.0, 90.0) is False
