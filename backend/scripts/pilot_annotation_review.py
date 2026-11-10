"""Create a non-destructive review artifact for pilot stroke annotations."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import cv2


REVIEW_FIELDS = [
    "annotation_id",
    "video_path",
    "start_ms",
    "end_ms",
    "duration_ms",
    "stroke_label",
    "annotation_status",
    "reviewer_id",
    "reviewer_label",
    "reviewer_start_ms",
    "reviewer_end_ms",
    "reviewer_status",
    "review_notes",
    "overlap_flag",
    "outside_video_duration_flag",
    "validation_error",
]

REQUIRED_FIELDS = {
    "annotation_id",
    "video_path",
    "stroke_label",
    "start_ms",
    "end_ms",
    "annotation_status",
}


@dataclass(frozen=True)
class AnnotationInterval:
    annotation_id: str
    video_path: str
    start_ms: float | None
    end_ms: float | None


def _read_annotations(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)
        missing = REQUIRED_FIELDS - set(reader.fieldnames or [])
        if missing:
            raise ValueError(
                "Annotation CSV is missing required columns: "
                + ", ".join(sorted(missing))
            )
        return [
            {key: (value or "") for key, value in row.items()}
            for row in reader
        ]


def _number(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _video_duration_ms(video_path: Path) -> float:
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise ValueError(f"Could not open source video: {video_path}")
    try:
        fps = float(capture.get(cv2.CAP_PROP_FPS))
        frame_count = float(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        if fps <= 0 or frame_count < 0:
            raise ValueError(
                f"Source video has invalid metadata: {video_path}"
            )
        return frame_count * 1000.0 / fps
    finally:
        capture.release()


def _intervals_overlap(
    first: AnnotationInterval,
    second: AnnotationInterval,
) -> bool:
    if first.video_path != second.video_path:
        return False
    if (
        first.start_ms is None
        or first.end_ms is None
        or second.start_ms is None
        or second.end_ms is None
    ):
        return False
    return (
        first.start_ms < second.end_ms
        and second.start_ms < first.end_ms
    )


def build_review_rows(
    annotations: Iterable[dict[str, str]],
    *,
    video_durations_ms: dict[str, float | None],
) -> list[dict[str, str]]:
    """Build review rows without changing annotation or reviewer decisions."""
    source_rows = list(annotations)
    intervals: list[AnnotationInterval] = []
    for row in source_rows:
        intervals.append(
            AnnotationInterval(
                annotation_id=row["annotation_id"],
                video_path=row["video_path"],
                start_ms=_number(row["start_ms"]),
                end_ms=_number(row["end_ms"]),
            )
        )

    overlaps = {
        interval.annotation_id
        for index, interval in enumerate(intervals)
        for other in intervals[index + 1 :]
        if _intervals_overlap(interval, other)
        for interval in (interval, other)
    }

    output: list[dict[str, str]] = []
    for row, interval in zip(source_rows, intervals):
        duration = (
            interval.end_ms - interval.start_ms
            if interval.start_ms is not None
            and interval.end_ms is not None
            else None
        )
        video_duration = video_durations_ms.get(interval.video_path)
        outside = (
            interval.start_ms is None
            or interval.end_ms is None
            or interval.start_ms < 0
            or interval.end_ms < 0
            or (
                video_duration is not None
                and interval.end_ms > video_duration
            )
        )
        errors: list[str] = []
        if interval.start_ms is None or interval.end_ms is None:
            errors.append("start_ms and end_ms must be numeric")
        elif interval.end_ms <= interval.start_ms:
            errors.append("end_ms must be greater than start_ms")
        if video_duration is None:
            errors.append("source video duration unavailable")

        output.append(
            {
                "annotation_id": row["annotation_id"],
                "video_path": row["video_path"],
                "start_ms": row["start_ms"],
                "end_ms": row["end_ms"],
                "duration_ms": "" if duration is None else str(duration),
                "stroke_label": row["stroke_label"],
                "annotation_status": row["annotation_status"],
                "reviewer_id": row.get("reviewer_id", ""),
                "reviewer_label": "",
                "reviewer_start_ms": "",
                "reviewer_end_ms": "",
                "reviewer_status": "",
                "review_notes": "",
                "overlap_flag": str(
                    interval.annotation_id in overlaps
                ).lower(),
                "outside_video_duration_flag": str(outside).lower(),
                "validation_error": "; ".join(errors),
            }
        )
    return output


def create_review_artifact(
    annotation_path: str | Path,
    output_path: str | Path,
    *,
    dataset_root: str | Path,
) -> Path:
    """Read annotations and write a separate CSV review artifact."""
    annotation_file = Path(annotation_path)
    root = Path(dataset_root)
    annotations = _read_annotations(annotation_file)
    video_paths = {
        row["video_path"]: root / row["video_path"]
        for row in annotations
    }
    durations = {
        relative_path: _video_duration_ms(video_path)
        for relative_path, video_path in video_paths.items()
    }
    rows = build_review_rows(
        annotations,
        video_durations_ms=durations,
    )
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=REVIEW_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a non-destructive pilot annotation review CSV."
    )
    parser.add_argument("annotation_csv", type=Path)
    parser.add_argument("output_csv", type=Path)
    parser.add_argument(
        "--dataset-root",
        type=Path,
        default=Path("."),
        help="Root used to resolve video_path values.",
    )
    args = parser.parse_args()
    create_review_artifact(
        args.annotation_csv,
        args.output_csv,
        dataset_root=args.dataset_root,
    )


if __name__ == "__main__":
    main()
