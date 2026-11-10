import csv

import pytest

from app.ml.dataset.io import (
    read_manifest_csv,
    write_manifest_csv,
)
from app.ml.dataset.manifest import DatasetRecord


def make_record(
    clip_id="clip_001",
    split="train",
):
    return DatasetRecord(
        clip_id=clip_id,
        clip_path=f"clips/{clip_id}.mp4",
        stroke_label="smash",
        source_video_id=f"video_{clip_id}",
        player_id="player_001",
        session_id="session_001",
        start_ms=1000.0,
        end_ms=2500.0,
        split=split,
        annotation_status="reviewed",
        reviewer_id="reviewer_001",
    )


def test_manifest_csv_round_trip(tmp_path):
    records = [
        make_record("clip_001", "train"),
        make_record("clip_002", "test"),
    ]

    csv_path = tmp_path / "manifests" / "dataset.csv"

    written_path = write_manifest_csv(records, csv_path)
    loaded_records = read_manifest_csv(csv_path)

    assert written_path == csv_path
    assert loaded_records == records


def test_writer_rejects_invalid_manifest(tmp_path):
    invalid_record = make_record()
    invalid_record = DatasetRecord(
        **{
            **invalid_record.__dict__,
            "end_ms": 500.0,
        }
    )

    with pytest.raises(ValueError, match="invalid manifest"):
        write_manifest_csv(
            [invalid_record],
            tmp_path / "dataset.csv",
        )


def test_reader_rejects_missing_required_columns(tmp_path):
    csv_path = tmp_path / "dataset.csv"

    with csv_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=["clip_id", "stroke_label"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "clip_id": "clip_001",
                "stroke_label": "smash",
            }
        )

    with pytest.raises(ValueError, match="missing required columns"):
        read_manifest_csv(csv_path)


def test_reader_rejects_invalid_timing_values(tmp_path):
    csv_path = tmp_path / "dataset.csv"

    records = [make_record()]

    write_manifest_csv(records, csv_path)

    rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))

    rows[0]["start_ms"] = "not-a-number"

    with csv_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=rows[0].keys(),
        )
        writer.writeheader()
        writer.writerows(rows)

    with pytest.raises(ValueError, match="timing value"):
        read_manifest_csv(csv_path)