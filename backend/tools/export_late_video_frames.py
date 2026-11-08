"""Export full-resolution, indexed frames from a later video segment."""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2


def export_frames(
    video_path: Path,
    output_dir: Path,
    start_frame: int,
    interval: int,
) -> list[Path]:
    """Export regular source-frame samples and always include the final frame."""
    if start_frame < 0:
        raise ValueError("start_frame must be non-negative")
    if interval < 1:
        raise ValueError("interval must be positive")

    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise ValueError(f"Could not open video: {video_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    try:
        frame_index = 0
        next_sample = start_frame
        last_frame_index: int | None = None
        last_frame = None
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            last_frame_index = frame_index
            last_frame = frame
            if frame_index == next_sample:
                written.append(_write_frame(frame, frame_index, output_dir))
                next_sample += interval
            frame_index += 1

        if last_frame_index is None or last_frame is None:
            raise ValueError(f"Video contains no readable frames: {video_path}")
        if last_frame_index >= start_frame and last_frame_index not in {
            _frame_index_from_path(path) for path in written
        }:
            written.append(_write_frame(last_frame, last_frame_index, output_dir))
    finally:
        capture.release()
    return written


def _write_frame(frame, frame_index: int, output_dir: Path) -> Path:
    annotated = frame.copy()
    cv2.putText(
        annotated,
        f"source frame {frame_index}",
        (24, 52),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.1,
        (0, 0, 0),
        5,
        cv2.LINE_AA,
    )
    cv2.putText(
        annotated,
        f"source frame {frame_index}",
        (24, 52),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.1,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )
    path = output_dir / f"frame_{frame_index:06d}.jpg"
    if not cv2.imwrite(str(path), annotated):
        raise ValueError(f"Could not write diagnostic frame: {path}")
    return path


def _frame_index_from_path(path: Path) -> int:
    return int(path.stem.removeprefix("frame_"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export full-resolution indexed frames from a later video segment."
    )
    parser.add_argument("video", type=Path, help="Source video path.")
    parser.add_argument("output_dir", type=Path, help="Diagnostic output directory.")
    parser.add_argument(
        "--start-frame",
        type=int,
        required=True,
        help="First zero-based source frame to sample.",
    )
    parser.add_argument(
        "--interval",
        type=int,
        required=True,
        help="Positive source-frame interval between regular samples.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    try:
        written = export_frames(
            args.video,
            args.output_dir,
            args.start_frame,
            args.interval,
        )
    except (OSError, ValueError) as error:
        raise SystemExit(str(error)) from error
    print(f"Exported {len(written)} full-resolution frames to {args.output_dir}")
    print("Source frame indices: " + ", ".join(
        str(_frame_index_from_path(path)) for path in written
    ))


if __name__ == "__main__":
    main()
