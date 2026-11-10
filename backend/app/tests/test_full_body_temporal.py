from types import SimpleNamespace

import pytest

from app.ml.features.full_body_temporal import (
    extract_full_body_temporal_features,
)


def make_point(x, y, valid=True):
    return SimpleNamespace(
        body_relative_x=x,
        body_relative_y=y,
        valid=valid,
    )


def make_position_frame(frame_index, timestamp_ms, x, y, valid=True):
    return SimpleNamespace(
        frame_index=frame_index,
        timestamp_ms=timestamp_ms,
        player_presence="PLAYER_PRESENT",
        keypoints={
            "right_wrist": make_point(x, y, valid=valid),
        },
    )


def make_angle_frame(frame_index, timestamp_ms, angle):
    return SimpleNamespace(
        frame_index=frame_index,
        timestamp_ms=timestamp_ms,
        angles_degrees={
            "right_elbow": angle,
        },
    )


def make_position_sequence(frames, fps=30.0):
    return SimpleNamespace(
        frames=frames,
        fps=fps,
        feature_schema="full_body",
        feature_version="1.0.0",
    )


def make_angle_sequence(frames, fps=30.0):
    return SimpleNamespace(
        frames=frames,
        fps=fps,
        feature_schema="joint_angles",
        feature_version="1.0.0",
    )


def extract(position_frames, angle_frames):
    return extract_full_body_temporal_features(
        make_position_sequence(position_frames),
        make_angle_sequence(angle_frames),
    )


def test_extracts_position_features():
    result = extract(
        [make_position_frame(0, 0, 0.1, 0.2)],
        [make_angle_frame(0, 0, 90.0)],
    )

    features = result.frames[0].features

    assert features["right_wrist_body_relative_x"] == pytest.approx(0.1)
    assert features["right_wrist_body_relative_y"] == pytest.approx(0.2)
    assert features["right_elbow_angle_degrees"] == pytest.approx(90.0)


def test_calculates_velocity_using_timestamps():
    result = extract(
        [
            make_position_frame(0, 0, 0.0, 0.0),
            make_position_frame(1, 1000, 3.0, 4.0),
        ],
        [
            make_angle_frame(0, 0, 90.0),
            make_angle_frame(1, 1000, 100.0),
        ],
    )

    # Displacement is 5 body-relative units over 1 second.
    assert (
        result.frames[1].features["right_wrist_velocity"]
        == pytest.approx(5.0)
    )


def test_calculates_angular_velocity():
    result = extract(
        [
            make_position_frame(0, 0, 0.0, 0.0),
            make_position_frame(1, 1000, 0.0, 0.0),
        ],
        [
            make_angle_frame(0, 0, 90.0),
            make_angle_frame(1, 1000, 120.0),
        ],
    )

    assert (
        result.frames[1].features["right_elbow_angular_velocity"]
        == pytest.approx(30.0)
    )


def test_calculates_acceleration_from_consecutive_velocities():
    result = extract(
        [
            make_position_frame(0, 0, 0.0, 0.0),
            make_position_frame(1, 1000, 1.0, 0.0),
            make_position_frame(2, 2000, 3.0, 0.0),
        ],
        [
            make_angle_frame(0, 0, 90.0),
            make_angle_frame(1, 1000, 90.0),
            make_angle_frame(2, 2000, 90.0),
        ],
    )

    # Speeds: 1 unit/s, then 2 units/s.
    # Speed acceleration: (2 - 1) / 1 = 1 unit/s².
    assert (
        result.frames[2].features["right_wrist_acceleration"]
        == pytest.approx(1.0)
    )


def test_stationary_point_has_zero_velocity():
    result = extract(
        [
            make_position_frame(0, 0, 0.5, 0.5),
            make_position_frame(1, 1000, 0.5, 0.5),
        ],
        [
            make_angle_frame(0, 0, 90.0),
            make_angle_frame(1, 1000, 90.0),
        ],
    )

    assert result.frames[1].features["right_wrist_velocity"] == 0.0


def test_missing_keypoint_does_not_create_fake_velocity():
    result = extract(
        [
            make_position_frame(0, 0, 0.0, 0.0, valid=False),
            make_position_frame(1, 1000, 1.0, 1.0, valid=True),
        ],
        [
            make_angle_frame(0, 0, 90.0),
            make_angle_frame(1, 1000, 100.0),
        ],
    )

    assert result.frames[1].features["right_wrist_velocity"] is None


def test_missing_angle_does_not_create_angular_velocity():
    result = extract(
        [
            make_position_frame(0, 0, 0.0, 0.0),
            make_position_frame(1, 1000, 1.0, 0.0),
        ],
        [
            make_angle_frame(0, 0, None),
            make_angle_frame(1, 1000, 100.0),
        ],
    )

    assert result.frames[1].features["right_elbow_angular_velocity"] is None


def test_first_frame_has_no_velocity_or_acceleration():
    result = extract(
        [
            make_position_frame(0, 0, 0.0, 0.0),
            make_position_frame(1, 1000, 1.0, 0.0),
        ],
        [
            make_angle_frame(0, 0, 90.0),
            make_angle_frame(1, 1000, 100.0),
        ],
    )

    first_features = result.frames[0].features

    assert first_features["right_wrist_velocity"] is None
    assert first_features["right_wrist_acceleration"] is None
    assert first_features["right_elbow_angular_velocity"] is None


def test_rejects_different_sequence_lengths():
    position_sequence = make_position_sequence(
        [make_position_frame(0, 0, 0.0, 0.0)]
    )

    angle_sequence = make_angle_sequence(
        [
            make_angle_frame(0, 0, 90.0),
            make_angle_frame(1, 1000, 100.0),
        ]
    )

    with pytest.raises(ValueError, match="same number of frames"):
        extract_full_body_temporal_features(
            position_sequence,
            angle_sequence,
        )


def test_rejects_misaligned_frame_indices():
    position_sequence = make_position_sequence(
        [make_position_frame(0, 0, 0.0, 0.0)]
    )

    angle_sequence = make_angle_sequence(
        [make_angle_frame(1, 0, 90.0)]
    )

    with pytest.raises(ValueError, match="frame indices must align"):
        extract_full_body_temporal_features(
            position_sequence,
            angle_sequence,
        )


def test_empty_sequences_return_empty_temporal_sequence():
    result = extract(
        [],
        [],
    )

    assert result.frames == []
    assert result.feature_schema == "full_body_temporal"
    assert result.feature_version == "1.0.0"