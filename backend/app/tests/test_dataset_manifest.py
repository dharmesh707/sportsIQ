import pytest

from app.ml.dataset.manifest import (
    DatasetRecord,
    audit_split_leakage,
    resolve_clip_path,
    validate_dataset_record,
    validate_manifest,
)


def make_record(
    clip_id="clip_001",
    source_video_id="video_001",
    player_id="player_001",
    split="train",
    start_ms=1000.0,
    end_ms=2500.0,
    annotation_status="reviewed",
):
    return DatasetRecord(
        clip_id=clip_id,
        clip_path=f"clips/{clip_id}.mp4",
        stroke_label="smash",
        source_video_id=source_video_id,
        player_id=player_id,
        session_id="session_001",
        start_ms=start_ms,
        end_ms=end_ms,
        split=split,
        annotation_status=annotation_status,
    )


def test_valid_dataset_record():
    result = validate_dataset_record(make_record())

    assert result.valid
    assert result.errors == []


def test_rejects_empty_required_fields():
    record = make_record(clip_id="")

    result = validate_dataset_record(record)

    assert not result.valid
    assert any("clip_id" in error for error in result.errors)


def test_rejects_invalid_split():
    record = make_record(split="testing")

    result = validate_dataset_record(record)

    assert not result.valid
    assert any("split must be one of" in error for error in result.errors)


def test_rejects_negative_start_time():
    record = make_record(start_ms=-100.0)

    result = validate_dataset_record(record)

    assert not result.valid
    assert any("start_ms" in error for error in result.errors)


def test_rejects_end_time_before_start_time():
    record = make_record(
        start_ms=2000.0,
        end_ms=1500.0,
    )

    result = validate_dataset_record(record)

    assert not result.valid
    assert any("end_ms" in error for error in result.errors)


def test_rejects_unreviewed_annotation():
    record = make_record(annotation_status="unreviewed")

    result = validate_dataset_record(record)

    assert not result.valid
    assert any("reviewed annotations" in error for error in result.errors)


def test_manifest_rejects_duplicate_clip_ids():
    records = [
        make_record(clip_id="clip_001"),
        make_record(
            clip_id="clip_001",
            source_video_id="video_002",
        ),
    ]

    result = validate_manifest(records)

    assert not result.valid
    assert any("Duplicate clip_id" in error for error in result.errors)


def test_detects_source_video_leakage():
    records = [
        make_record(
            clip_id="clip_train",
            source_video_id="same_video",
            split="train",
        ),
        make_record(
            clip_id="clip_test",
            source_video_id="same_video",
            split="test",
        ),
    ]

    report = audit_split_leakage(records)

    assert report.has_source_video_leakage
    assert report.source_video_leakage["same_video"] == [
        "test",
        "train",
    ]


def test_detects_player_overlap_between_splits():
    records = [
        make_record(
            clip_id="clip_train",
            source_video_id="video_train",
            player_id="same_player",
            split="train",
        ),
        make_record(
            clip_id="clip_test",
            source_video_id="video_test",
            player_id="same_player",
            split="test",
        ),
    ]

    report = audit_split_leakage(records)

    assert report.has_player_leakage
    assert report.player_leakage["same_player"] == [
        "test",
        "train",
    ]


def test_no_leakage_when_groups_are_disjoint():
    records = [
        make_record(
            clip_id="clip_train",
            source_video_id="video_train",
            player_id="player_train",
            split="train",
        ),
        make_record(
            clip_id="clip_test",
            source_video_id="video_test",
            player_id="player_test",
            split="test",
        ),
    ]

    report = audit_split_leakage(records)

    assert not report.has_any_leakage


def test_resolves_path_inside_dataset_root(tmp_path):
    result = resolve_clip_path(
        tmp_path,
        "clips/clip_001.mp4",
    )

    assert result == tmp_path.resolve() / "clips" / "clip_001.mp4"


def test_rejects_path_that_escapes_dataset_root(tmp_path):
    with pytest.raises(ValueError, match="inside the dataset root"):
        resolve_clip_path(
            tmp_path,
            "../outside.mp4",
        )