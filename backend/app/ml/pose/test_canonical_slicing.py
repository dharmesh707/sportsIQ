
from __future__ import annotations

import pytest

from app.ml.pose.canonical import (
    CANONICAL_KEYPOINT_NAMES,
    CanonicalPoseSequence,
    FramePoseObservation,
    KeypointObservation,
)
from app.ml.pose.canonical_slicing import (
    slice_canonical_pose_sequence,
)


def make_frame(
    frame_index: int,
    timestamp_ms: int,
) -> FramePoseObservation:
    """Create a valid canonical frame for testing."""

    keypoints = {
        name: KeypointObservation.missing()
        for name in CANONICAL_KEYPOINT_NAMES
    }

    return FramePoseObservation(
        frame_index=frame_index,
        timestamp_ms=timestamp_ms,
        width_px=1920,
        height_px=1080,
        keypoints=keypoints,
        player_presence="UNCERTAIN",
    )


@pytest.fixture
def canonical_sequence() -> CanonicalPoseSequence:
    """Create a small canonical sequence with known timestamps."""

    frames = (
        make_frame(0, 0),
        make_frame(1, 100),
        make_frame(2, 200),
        make_frame(3, 300),
        make_frame(4, 400),
    )

    return CanonicalPoseSequence(
        frames=frames,
        estimator_name="test_estimator",
        estimator_version="1.0",
        model_name="test_model",
        schema_name="sportsiq.canonical_pose",
        schema_version="1.0",
        fps=10.0,
    )


def test_slice_uses_start_inclusive_end_exclusive(
    canonical_sequence: CanonicalPoseSequence,
) -> None:
    result = slice_canonical_pose_sequence(
        canonical_sequence,
        start_ms=100,
        end_ms=300,
    )

    assert [frame.timestamp_ms for frame in result.frames] == [
        100,
        200,
    ]


def test_slice_preserves_original_frame_indices(
    canonical_sequence: CanonicalPoseSequence,
) -> None:
    result = slice_canonical_pose_sequence(
        canonical_sequence,
        start_ms=100,
        end_ms=300,
    )

    assert [frame.frame_index for frame in result.frames] == [
        1,
        2,
    ]


def test_slice_preserves_sequence_metadata(
    canonical_sequence: CanonicalPoseSequence,
) -> None:
    result = slice_canonical_pose_sequence(
        canonical_sequence,
        start_ms=100,
        end_ms=300,
    )

    assert result.estimator_name == canonical_sequence.estimator_name
    assert result.estimator_version == canonical_sequence.estimator_version
    assert result.model_name == canonical_sequence.model_name
    assert result.coordinate_metadata == canonical_sequence.coordinate_metadata
    assert result.schema_name == canonical_sequence.schema_name
    assert result.schema_version == canonical_sequence.schema_version
    assert result.fps == canonical_sequence.fps


@pytest.mark.parametrize(
    ("start_ms", "end_ms"),
    [
        (-1, 100),
        (100, 100),
        (200, 100),
    ],
)
def test_slice_rejects_invalid_interval(
    canonical_sequence: CanonicalPoseSequence,
    start_ms: float,
    end_ms: float,
) -> None:
    with pytest.raises(ValueError):
        slice_canonical_pose_sequence(
            canonical_sequence,
            start_ms=start_ms,
            end_ms=end_ms,
        )
