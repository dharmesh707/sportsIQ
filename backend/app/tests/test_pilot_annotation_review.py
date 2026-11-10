import csv

import scripts.pilot_annotation_review as review
from scripts.pilot_annotation_review import (
    REVIEW_FIELDS,
    build_review_rows,
    create_review_artifact,
)


def annotation(
    annotation_id: str,
    start_ms: str,
    end_ms: str,
    video_path: str = "video.mp4",
) -> dict[str, str]:
    return {
        "annotation_id": annotation_id,
        "video_path": video_path,
        "stroke_label": "smash",
        "start_ms": start_ms,
        "end_ms": end_ms,
        "annotation_status": "pending_review",
        "reviewer_id": "",
    }


def test_review_rows_flag_overlap_and_keep_reviewer_fields_blank():
    rows = build_review_rows(
        [
            annotation("first", "100", "300"),
            annotation("second", "250", "400"),
        ],
        video_durations_ms={"video.mp4": 1000.0},
    )

    assert [row["duration_ms"] for row in rows] == ["200.0", "150.0"]
    assert [row["overlap_flag"] for row in rows] == ["true", "true"]
    assert all(row["outside_video_duration_flag"] == "false" for row in rows)
    assert all(row["reviewer_label"] == "" for row in rows)
    assert all(row["reviewer_status"] == "" for row in rows)
    assert all(row["annotation_status"] == "pending_review" for row in rows)


def test_review_rows_flag_outside_and_invalid_intervals():
    rows = build_review_rows(
        [
            annotation("outside", "-1", "1100"),
            annotation("invalid", "500", "400"),
            annotation("malformed", "bad", "600"),
        ],
        video_durations_ms={"video.mp4": 1000.0},
    )

    assert rows[0]["outside_video_duration_flag"] == "true"
    assert rows[0]["validation_error"] == ""
    assert rows[1]["validation_error"] == "end_ms must be greater than start_ms"
    assert rows[2]["validation_error"] == "start_ms and end_ms must be numeric"


def test_create_review_artifact_does_not_modify_source(tmp_path, monkeypatch):
    source = tmp_path / "annotations.csv"
    output = tmp_path / "review" / "annotations_review.csv"
    source.write_text(
        "annotation_id,video_path,stroke_label,start_ms,end_ms,"
        "annotation_status,reviewer_id\n"
        "a,video.mp4,smash,100,200,pending_review,\n",
        encoding="utf-8",
    )
    source_before = source.read_bytes()
    monkeypatch.setattr(
        review,
        "_video_duration_ms",
        lambda video_path: 1000.0,
    )

    create_review_artifact(
        source,
        output,
        dataset_root=tmp_path,
    )

    assert source.read_bytes() == source_before
    with output.open(newline="", encoding="utf-8") as csv_file:
        rows = list(csv.DictReader(csv_file))
    assert rows[0]["annotation_id"] == "a"
    assert list(rows[0]) == REVIEW_FIELDS
    assert rows[0]["reviewer_start_ms"] == ""
