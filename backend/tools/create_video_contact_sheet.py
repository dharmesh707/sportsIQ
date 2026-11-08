"""Create an indexed contact sheet for manual video review."""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np


def create_contact_sheet(
    video_path: Path,
    output_path: Path,
    columns: int = 6,
    thumbnail_width: int = 160,
    label_height: int = 28,
) -> int:
    """Write all readable source frames with zero-based frame labels."""
    if columns < 1:
        raise ValueError("columns must be positive")
    if thumbnail_width < 1:
        raise ValueError("thumbnail_width must be positive")
    if label_height < 1:
        raise ValueError("label_height must be positive")

    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise ValueError(f"Could not open video: {video_path}")

    thumbnails: list[np.ndarray] = []
    try:
        frame_index = 0
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            height, width = frame.shape[:2]
            thumbnail_height = max(1, round(height * thumbnail_width / width))
            thumbnail = cv2.resize(
                frame,
                (thumbnail_width, thumbnail_height),
                interpolation=cv2.INTER_AREA,
            )
            canvas = np.zeros(
                (label_height + thumbnail_height, thumbnail_width, 3),
                dtype=np.uint8,
            )
            canvas[label_height:] = thumbnail
            cv2.putText(
                canvas,
                f"frame {frame_index}",
                (6, 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.52,
                (255, 255, 255),
                1,
                cv2.LINE_AA,
            )
            thumbnails.append(canvas)
            frame_index += 1
    finally:
        capture.release()

    if not thumbnails:
        raise ValueError(f"Video contains no readable frames: {video_path}")

    rows = (len(thumbnails) + columns - 1) // columns
    cell_height = thumbnails[0].shape[0]
    sheet = np.zeros(
        (rows * cell_height, columns * thumbnail_width, 3),
        dtype=np.uint8,
    )
    for index, thumbnail in enumerate(thumbnails):
        row, column = divmod(index, columns)
        y = row * cell_height
        x = column * thumbnail_width
        sheet[y:y + cell_height, x:x + thumbnail_width] = thumbnail

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(output_path), sheet):
        raise ValueError(f"Could not write contact sheet: {output_path}")
    return len(thumbnails)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create an indexed contact sheet for manual video review."
    )
    parser.add_argument("video", type=Path, help="Source video path.")
    parser.add_argument("output", type=Path, help="Contact-sheet image path.")
    parser.add_argument(
        "--columns",
        type=int,
        default=6,
        help="Number of thumbnails per row (default: 6).",
    )
    parser.add_argument(
        "--thumbnail-width",
        type=int,
        default=160,
        help="Thumbnail width in pixels (default: 160).",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    try:
        frame_count = create_contact_sheet(
            args.video,
            args.output,
            columns=args.columns,
            thumbnail_width=args.thumbnail_width,
        )
    except (OSError, ValueError) as error:
        raise SystemExit(str(error)) from error
    print(f"Contact sheet: {args.output}")
    print(f"Frames included: {frame_count} (indices 0-{frame_count - 1})")


if __name__ == "__main__":
    main()
