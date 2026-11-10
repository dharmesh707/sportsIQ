from __future__ import annotations

import csv
from pathlib import Path

from app.ml.dataset.manifest import (
    DatasetRecord,
    validate_manifest,
)


MANIFEST_FIELDS = [
    "clip_id",
    "clip_path",
    "stroke_label",
    "source_video_id",
    "player_id",
    "session_id",
    "start_ms",
    "end_ms",
    "split",
    "annotation_status",
    "reviewer_id",
]


def write_manifest_csv(
    records: list[DatasetRecord],
    path: str | Path,
) -> Path:
    """
    Validate and write dataset records to a CSV manifest.

    Parent directories are created when needed.
    Invalid manifests are rejected before writing.
    """
    validation = validate_manifest(records)

    if not validation.valid:
        raise ValueError(
            "Cannot write invalid manifest:\n"
            + "\n".join(validation.errors)
        )

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=MANIFEST_FIELDS,
        )

        writer.writeheader()

        for record in records:
            writer.writerow(
                {
                    "clip_id": record.clip_id,
                    "clip_path": record.clip_path,
                    "stroke_label": record.stroke_label,
                    "source_video_id": record.source_video_id,
                    "player_id": record.player_id,
                    "session_id": record.session_id,
                    "start_ms": record.start_ms,
                    "end_ms": record.end_ms,
                    "split": record.split,
                    "annotation_status": record.annotation_status,
                    "reviewer_id": record.reviewer_id or "",
                }
            )

    return output_path


def read_manifest_csv(
    path: str | Path,
    *,
    validate: bool = True,
) -> list[DatasetRecord]:
    """
    Read dataset records from a CSV manifest.

    When validate=True, rejects invalid records and duplicate clip IDs.
    """
    input_path = Path(path)

    if not input_path.exists():
        raise FileNotFoundError(
            f"Manifest file does not exist: {input_path}"
        )

    records: list[DatasetRecord] = []

    with input_path.open(
        "r",
        newline="",
        encoding="utf-8-sig",
    ) as csv_file:
        reader = csv.DictReader(csv_file)

        missing_fields = set(MANIFEST_FIELDS) - set(
            reader.fieldnames or []
        )

        if missing_fields:
            raise ValueError(
                "Manifest is missing required columns: "
                + ", ".join(sorted(missing_fields))
            )

        for row_number, row in enumerate(reader, start=2):
            try:
                start_ms = float(row["start_ms"])
                end_ms = float(row["end_ms"])
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"Invalid timing value on CSV row {row_number}."
                ) from exc

            records.append(
                DatasetRecord(
                    clip_id=row["clip_id"],
                    clip_path=row["clip_path"],
                    stroke_label=row["stroke_label"],
                    source_video_id=row["source_video_id"],
                    player_id=row["player_id"],
                    session_id=row["session_id"],
                    start_ms=start_ms,
                    end_ms=end_ms,
                    split=row["split"],
                    annotation_status=row["annotation_status"],
                    reviewer_id=row["reviewer_id"] or None,
                )
            )

    if validate:
        validation = validate_manifest(records)

        if not validation.valid:
            raise ValueError(
                "Invalid manifest:\n"
                + "\n".join(validation.errors)
            )

    return records