"""Tests for canonical full-body candidate-window segmentation."""

import pytest

from app.ml.pose.canonical import (
    CANONICAL_KEYPOINT_NAMES,
    CanonicalPoseSequence,
    FramePoseObservation,
    KeypointObservation,
)
from app.ml.pose.segmentation import segment_pose_sequence


def make_frame(
    frame_index: int,
    *,
    player_presence: str = "PLAYER_PRESENT",
) -> FramePoseObservation:
    """Create a minimal canonical frame for segmentation tests."""

    keypoints = {
        name: KeypointObservation.missing()
        for name in CANONICAL_KEYPOINT_NAMES
    }

    return FramePoseObservation(
        frame_index=frame_index,
        timestamp_ms=frame_index * 33,
        width_px=640,
        height_px=480,
        keypoints=keypoints,
        player_presence=player_presence,
    )


def make_sequence(
    frame_count: int,
    *,
    absent_frames: set[int] | None = None,
) -> CanonicalPoseSequence:
    """Create a synthetic canonical pose sequence."""

    absent_frames = absent_frames or set()

    frames = tuple(
        make_frame(
            index,
            player_presence=(
                "PLAYER_ABSENT"
                if index in absent_frames
                else "PLAYER_PRESENT"
            ),
        )
        for index in range(frame_count)
    )

    return CanonicalPoseSequence(
        frames=frames,
        estimator_name="test-estimator",
        estimator_version="1.0",
        model_name="test-model",
        fps=30.0,
    )


def test_generates_windows_with_expected_stride():
    sequence = make_sequence(100)

    windows = segment_pose_sequence(
        sequence,
        window_size_frames=60,
        stride_frames=15,
    )

    assert len(windows) == 3

    assert [
        window.start_frame_index
        for window in windows
    ] == [0, 15, 30]

    assert [
        window.end_frame_index
        for window in windows
    ] == [59, 74, 89]


def test_drops_incomplete_final_window_by_default():
    sequence = make_sequence(70)

    windows = segment_pose_sequence(
        sequence,
        window_size_frames=60,
        stride_frames=15,
    )

    assert len(windows) == 1
    assert windows[0].start_frame_index == 0
    assert windows[0].end_frame_index == 59


def test_can_include_incomplete_final_window():
    sequence = make_sequence(70)

    windows = segment_pose_sequence(
        sequence,
        window_size_frames=60,
        stride_frames=15,
        include_partial_window=True,
    )

    assert len(windows) == 2

    assert windows[1].start_frame_index == 15
    assert windows[1].end_frame_index == 69
    assert len(windows[1].frames) == 55


def test_filters_windows_with_low_player_presence():
    sequence = make_sequence(
        60,
        absent_frames=set(range(0, 20)),
    )

    windows = segment_pose_sequence(
        sequence,
        window_size_frames=60,
        stride_frames=60,
        min_player_presence_ratio=0.7,
    )

    assert windows == ()


def test_keeps_window_at_presence_threshold():
    sequence = make_sequence(
        60,
        absent_frames=set(range(0, 18)),
    )

    windows = segment_pose_sequence(
        sequence,
        window_size_frames=60,
        stride_frames=60,
        min_player_presence_ratio=0.7,
    )

    assert len(windows) == 1
    assert windows[0].player_presence_ratio == pytest.approx(0.7)


def test_preserves_timestamps_and_frame_indices():
    sequence = make_sequence(60)

    windows = segment_pose_sequence(
        sequence,
        window_size_frames=60,
        stride_frames=60,
    )

    window = windows[0]

    assert window.start_frame_index == 0
    assert window.end_frame_index == 59

    assert window.start_timestamp_ms == 0
    assert window.end_timestamp_ms == 59 * 33


def test_empty_sequence_returns_no_windows():
    sequence = make_sequence(0)

    windows = segment_pose_sequence(
        sequence,
        window_size_frames=60,
        stride_frames=15,
    )

    assert windows == ()


@pytest.mark.parametrize(
    ("window_size", "stride"),
    [
        (0, 10),
        (-1, 10),
        (10, 0),
        (10, -1),
    ],
)
def test_rejects_invalid_window_parameters(
    window_size: int,
    stride: int,
):
    sequence = make_sequence(60)

    with pytest.raises(ValueError):
        segment_pose_sequence(
            sequence,
            window_size_frames=window_size,
            stride_frames=stride,
        )