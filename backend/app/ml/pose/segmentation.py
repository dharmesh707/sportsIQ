"""Candidate-window segmentation for canonical full-body pose sequences."""

from __future__ import annotations

from dataclasses import dataclass

from app.ml.pose.canonical import (
    CanonicalPoseSequence,
    FramePoseObservation,
)


@dataclass(frozen=True)
class CandidatePoseWindow:
    """A fixed-length candidate window from a canonical pose sequence."""

    frames: tuple[FramePoseObservation, ...]

    start_frame_index: int
    end_frame_index: int

    start_timestamp_ms: int
    end_timestamp_ms: int

    player_presence_ratio: float

    def __post_init__(self) -> None:
        if not self.frames:
            raise ValueError("Candidate window cannot be empty")

        if self.start_frame_index != self.frames[0].frame_index:
            raise ValueError("start_frame_index does not match first frame")

        if self.end_frame_index != self.frames[-1].frame_index:
            raise ValueError("end_frame_index does not match last frame")

        if self.start_timestamp_ms != self.frames[0].timestamp_ms:
            raise ValueError("start_timestamp_ms does not match first frame")

        if self.end_timestamp_ms != self.frames[-1].timestamp_ms:
            raise ValueError("end_timestamp_ms does not match last frame")

        if not 0.0 <= self.player_presence_ratio <= 1.0:
            raise ValueError("player_presence_ratio must be between 0 and 1")


def segment_pose_sequence(
    sequence: CanonicalPoseSequence,
    *,
    window_size_frames: int,
    stride_frames: int,
    min_player_presence_ratio: float = 0.7,
    include_partial_window: bool = False,
) -> tuple[CandidatePoseWindow, ...]:
    """
    Generate candidate windows from a canonical full-body pose sequence.

    Windows are created using source-frame order. A window is retained only
    when its PLAYER_PRESENT ratio meets the configured threshold.

    This function does not identify badminton strokes or infer action
    boundaries. It creates candidate windows for subsequent review/labeling.
    """
    if window_size_frames <= 0:
        raise ValueError("window_size_frames must be positive")

    if stride_frames <= 0:
        raise ValueError("stride_frames must be positive")

    if not 0.0 <= min_player_presence_ratio <= 1.0:
        raise ValueError(
            "min_player_presence_ratio must be between 0 and 1"
        )

    frames = sequence.frames

    if not frames:
        return ()

    windows: list[CandidatePoseWindow] = []

    start = 0

    while start < len(frames):
        end = start + window_size_frames

        if end > len(frames):
            if not include_partial_window:
                break

            window_frames = frames[start:]
        else:
            window_frames = frames[start:end]

        if not window_frames:
            break

        present_count = sum(
            frame.player_presence == "PLAYER_PRESENT"
            for frame in window_frames
        )

        presence_ratio = present_count / len(window_frames)

        if presence_ratio >= min_player_presence_ratio:
            windows.append(
                CandidatePoseWindow(
                    frames=tuple(window_frames),
                    start_frame_index=window_frames[0].frame_index,
                    end_frame_index=window_frames[-1].frame_index,
                    start_timestamp_ms=window_frames[0].timestamp_ms,
                    end_timestamp_ms=window_frames[-1].timestamp_ms,
                    player_presence_ratio=presence_ratio,
                )
            )

        if end >= len(frames):
            break

        start += stride_frames

    return tuple(windows)