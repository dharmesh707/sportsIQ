import pytest

from app.ml.pose.sequence import (
    PoseSequence,
    PoseFrame,
    slice_pose_sequence,
)


def make_frame(frame_index: int, timestamp_ms: int) -> PoseFrame:
    return PoseFrame(
        frame_index=frame_index,
        timestamp_ms=timestamp_ms,
        left=None,
        right=None,
    )


def test_slice_pose_sequence_includes_start_and_excludes_end_boundary():
    sequence = PoseSequence(
        frames=(
            make_frame(0, 0),
            make_frame(30, 1000),
            make_frame(60, 2000),
            make_frame(90, 3000),
        ),
        fps=30.0,
        racket_side="unknown",
    )

    sliced = slice_pose_sequence(
        sequence,
        start_ms=1000,
        end_ms=2000,
    )

    assert [frame.frame_index for frame in sliced.frames] == [30]
    assert [frame.timestamp_ms for frame in sliced.frames] == [1000]


def test_slice_pose_sequence_preserves_original_timeline():
    sequence = PoseSequence(
        frames=(
            make_frame(0, 0),
            make_frame(30, 1000),
            make_frame(60, 2000),
        ),
        fps=30.0,
        racket_side="unknown",
    )

    sliced = slice_pose_sequence(
        sequence,
        start_ms=1000,
        end_ms=2000,
    )

    assert sliced.frames[0].frame_index == 30
    assert sliced.frames[0].timestamp_ms == 1000


def test_slice_pose_sequence_rejects_invalid_interval():
    sequence = PoseSequence(
        frames=(make_frame(0, 0),),
        fps=30.0,
        racket_side="unknown",
    )

    with pytest.raises(ValueError):
        slice_pose_sequence(sequence, start_ms=-1, end_ms=1000)

    with pytest.raises(ValueError):
        slice_pose_sequence(sequence, start_ms=1000, end_ms=1000)

    with pytest.raises(ValueError):
        slice_pose_sequence(sequence, start_ms=1000, end_ms=999)


def test_slice_pose_sequence_returns_empty_when_no_frames_match():
    sequence = PoseSequence(
        frames=(
            make_frame(0, 0),
            make_frame(30, 1000),
        ),
        fps=30.0,
        racket_side="unknown",
    )

    sliced = slice_pose_sequence(
        sequence,
        start_ms=2000,
        end_ms=3000,
    )

    assert sliced.frames == ()