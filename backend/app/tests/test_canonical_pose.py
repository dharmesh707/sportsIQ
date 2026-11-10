import json
from typing import MutableMapping, cast

import pytest

from app.ml.pose.canonical import (
    CANONICAL_KEYPOINT_NAMES,
    CanonicalPoseSequence,
    CoordinateMetadata,
    FramePoseObservation,
    KeypointObservation,
)


def _keypoints():
    return {
        name: KeypointObservation(
            present=True,
            x_norm=0.25,
            y_norm=0.5,
            z_native=-0.1,
            confidence=0.8 if name == "right_wrist" else None,
        )
        for name in CANONICAL_KEYPOINT_NAMES
    }


def _frame(index=0, timestamp=0, keypoints=None):
    return FramePoseObservation(
        frame_index=index,
        timestamp_ms=timestamp,
        width_px=608,
        height_px=1080,
        keypoints=keypoints or _keypoints(),
    )


def test_constructs_valid_full_body_pose_with_optional_confidence():
    frame = _frame()

    assert len(frame.keypoints) == 21
    assert frame.keypoints["right_wrist"].confidence == 0.8
    assert frame.keypoints["left_wrist"].confidence is None


def test_missing_keypoint_is_explicit():
    keypoints = _keypoints()
    keypoints["left_ankle"] = KeypointObservation.missing()

    assert not _frame(keypoints=keypoints).keypoints["left_ankle"].present


def test_coordinate_metadata_is_preserved():
    metadata = CoordinateMetadata(
        world_convention="mediapipe_world_native"
    )

    sequence = CanonicalPoseSequence(
        frames=(_frame(),),
        estimator_name="mediapipe",
        estimator_version="1.0.1",
        model_name="pose_landmarker_full.task",
        coordinate_metadata=metadata,
        fps=26.0,
    )

    assert sequence.coordinate_metadata == metadata
    assert (
        sequence.to_dict()["coordinate_policy"]["z_convention"]
        == "estimator_native"
    )


@pytest.mark.parametrize("field", ["width_px", "height_px"])
def test_invalid_image_dimensions_are_rejected(field):
    values = {
        "width_px": 608,
        "height_px": 1080,
    }
    values[field] = 0

    with pytest.raises(ValueError, match="positive integer"):
        FramePoseObservation(
            frame_index=0,
            timestamp_ms=0,
            keypoints=_keypoints(),
            width_px=values["width_px"],
            height_px=values["height_px"],
        )


def test_non_finite_coordinates_are_rejected():
    with pytest.raises(ValueError, match="x_norm must be finite"):
        KeypointObservation(
            present=True,
            x_norm=float("nan"),
            y_norm=0.5,
        )


def test_invalid_timestamps_are_rejected():
    with pytest.raises(ValueError, match="timestamp_ms"):
        _frame(timestamp=-1)


def test_sequence_requires_ordered_frames():
    with pytest.raises(ValueError, match="frame_index"):
        CanonicalPoseSequence(
            frames=(
                _frame(1, 0),
                _frame(1, 40),
            ),
            estimator_name="mediapipe",
            estimator_version=None,
            model_name=None,
        )


def test_sequence_serializes_and_deserializes():
    sequence = CanonicalPoseSequence(
        frames=(
            _frame(0, 0),
            _frame(1, 40),
        ),
        estimator_name="mediapipe",
        estimator_version="1.0.1",
        model_name="pose_landmarker_full.task",
        fps=25.0,
    )

    encoded = json.dumps(sequence.to_dict())
    restored = CanonicalPoseSequence.from_dict(json.loads(encoded))

    assert restored == sequence


def test_frame_keypoints_mapping_is_immutable():
    original_keypoints = _keypoints()
    frame = _frame(keypoints=original_keypoints)

    # Mutating the original mapping must not mutate the frame.
    original_keypoints["left_wrist"] = KeypointObservation.missing()

    assert frame.keypoints["left_wrist"].present is True

    # Mutating the frame's mapping must fail.
    with pytest.raises(TypeError):
        cast(MutableMapping[str, KeypointObservation], frame.keypoints)[
            "left_wrist"
        ] = KeypointObservation.missing()


@pytest.mark.parametrize("fps", [True, False])
def test_sequence_rejects_boolean_fps(fps):
    with pytest.raises(ValueError, match="fps"):
        CanonicalPoseSequence(
            frames=(_frame(),),
            estimator_name="mediapipe",
            estimator_version="1.0.1",
            model_name="pose_landmarker_full.task",
            fps=fps,
        )