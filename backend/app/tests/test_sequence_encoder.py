from types import SimpleNamespace

import pytest

from app.ml.features.sequence_encoder import encode_temporal_sequence


def make_frame(frame_index, timestamp_ms, features):
    return SimpleNamespace(
        frame_index=frame_index,
        timestamp_ms=timestamp_ms,
        features=features,
    )


def make_sequence(frames):
    return SimpleNamespace(
        frames=frames,
        fps=30.0,
        feature_schema="full_body_temporal",
        feature_version="1.0.0",
    )


def test_encodes_sequence_to_requested_length():
    sequence = make_sequence(
        [
            make_frame(0, 0, {"wrist_velocity": 0.0}),
            make_frame(1, 100, {"wrist_velocity": 10.0}),
            make_frame(2, 200, {"wrist_velocity": 20.0}),
        ]
    )

    result = encode_temporal_sequence(sequence, target_length=5)

    assert len(result.values) == 5
    assert all(len(row) == 1 for row in result.values)
    assert result.target_length == 5


def test_preserves_feature_order():
    sequence = make_sequence(
        [
            make_frame(
                0,
                0,
                {
                    "z_feature": 1.0,
                    "a_feature": 2.0,
                },
            ),
            make_frame(
                1,
                100,
                {
                    "z_feature": 3.0,
                    "a_feature": 4.0,
                },
            ),
        ]
    )

    result = encode_temporal_sequence(sequence, target_length=2)

    assert result.feature_names == ["a_feature", "z_feature"]
    assert result.values[0] == [2.0, 1.0]
    assert result.values[1] == [4.0, 3.0]


def test_interpolates_between_observations():
    sequence = make_sequence(
        [
            make_frame(0, 0, {"feature": 0.0}),
            make_frame(1, 100, {"feature": 10.0}),
        ]
    )

    result = encode_temporal_sequence(sequence, target_length=3)

    assert result.values[0][0] == pytest.approx(0.0)
    assert result.values[1][0] == pytest.approx(5.0)
    assert result.values[2][0] == pytest.approx(10.0)


def test_missing_values_are_interpolated_only_between_valid_points():
    sequence = make_sequence(
        [
            make_frame(0, 0, {"feature": 0.0}),
            make_frame(1, 100, {"feature": None}),
            make_frame(2, 200, {"feature": 20.0}),
        ]
    )

    result = encode_temporal_sequence(sequence, target_length=5)

    assert result.values[0][0] == pytest.approx(0.0)
    assert result.values[1][0] == pytest.approx(5.0)
    assert result.values[2][0] == pytest.approx(10.0)
    assert result.values[3][0] == pytest.approx(15.0)
    assert result.values[4][0] == pytest.approx(20.0)


def test_does_not_extrapolate_before_first_valid_observation():
    sequence = make_sequence(
        [
            make_frame(0, 0, {"feature": None}),
            make_frame(1, 100, {"feature": 10.0}),
            make_frame(2, 200, {"feature": 20.0}),
        ]
    )

    result = encode_temporal_sequence(sequence, target_length=5)

    # Target timestamps: 0, 50, 100, 150, 200 ms.
    # The first valid observation is at 100 ms.
    assert result.values[0][0] is None
    assert result.values[1][0] is None

    # Exact observation at 100 ms.
    assert result.values[2][0] == pytest.approx(10.0)

    # Interpolation between 10 at 100 ms and 20 at 200 ms.
    assert result.values[3][0] == pytest.approx(15.0)

    # Exact observation at 200 ms.
    assert result.values[4][0] == pytest.approx(20.0)

def test_feature_with_no_valid_values_remains_none():
    sequence = make_sequence(
        [
            make_frame(0, 0, {"feature": None}),
            make_frame(1, 100, {"feature": None}),
        ]
    )

    result = encode_temporal_sequence(sequence, target_length=4)

    assert all(row[0] is None for row in result.values)


def test_one_frame_sequence_can_be_encoded():
    sequence = make_sequence(
        [
            make_frame(
                0,
                100,
                {
                    "feature": 5.0,
                },
            )
        ]
    )

    result = encode_temporal_sequence(sequence, target_length=4)

    assert len(result.values) == 4
    assert all(row == [5.0] for row in result.values)


def test_rejects_empty_sequence():
    sequence = make_sequence([])

    with pytest.raises(ValueError, match="empty"):
        encode_temporal_sequence(sequence)


def test_rejects_invalid_target_length():
    sequence = make_sequence(
        [
            make_frame(0, 0, {"feature": 1.0}),
        ]
    )

    with pytest.raises(ValueError, match="at least 1"):
        encode_temporal_sequence(sequence, target_length=0)


def test_rejects_non_increasing_timestamps():
    sequence = make_sequence(
        [
            make_frame(0, 100, {"feature": 1.0}),
            make_frame(1, 100, {"feature": 2.0}),
        ]
    )

    with pytest.raises(ValueError, match="strictly increasing"):
        encode_temporal_sequence(sequence)