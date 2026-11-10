from __future__ import annotations

from dataclasses import replace

from app.ml.pose.canonical import CanonicalPoseSequence


def slice_canonical_pose_sequence(
    sequence: CanonicalPoseSequence,
    start_ms: float,
    end_ms: float,
) -> CanonicalPoseSequence:
    """
    Slice a canonical pose sequence using source-video timestamps.

    The interval is [start_ms, end_ms): start inclusive, end exclusive.

    Frame indices and timestamps remain those of the original source
    video. They are not reset to zero.
    """
    if start_ms < 0:
        raise ValueError("start_ms must be non-negative.")

    if end_ms <= start_ms:
        raise ValueError("end_ms must be greater than start_ms.")

    selected_frames = tuple(
        frame
        for frame in sequence.frames
        if start_ms <= frame.timestamp_ms < end_ms
    )

    return replace(
        sequence,
        frames=selected_frames,
    )