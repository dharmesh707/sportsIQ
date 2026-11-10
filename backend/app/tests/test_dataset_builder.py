from types import SimpleNamespace

import pytest

from app.ml.dataset.builder import build_feature_dataset
from app.ml.dataset.manifest import DatasetRecord
from app.ml.features.full_body_temporal import (
    TemporalFeatureFrame,
    TemporalFeatureSequence,
)


def make_record(
    clip_id="clip_001",
    source_video_id="video_001",
    player_id="player_001",
    split="train",
    label="smash",
):
    return DatasetRecord(
        clip_id=clip_id,
        clip_path=f"clips/{clip_id}.mp4",
        stroke_label=label,
        source_video_id=source_video_id,
        player_id=player_id,
        session_id="session_001",
        start_ms=0.0,
        end_ms=200.0,
        split=split,
        annotation_status="reviewed",
    )


def make_temporal_sequence():
    return TemporalFeatureSequence(
        frames=[
            TemporalFeatureFrame(
                frame_index=0,
                timestamp_ms=0.0,
                features={
                    "wrist_velocity": 0.0,
                    "elbow_angle": 90.0,
                },
            ),
            TemporalFeatureFrame(
                frame_index=1,
                timestamp_ms=100.0,
                features={
                    "wrist_velocity": 5.0,
                    "elbow_angle": 100.0,
                },
            ),
            TemporalFeatureFrame(
                frame_index=2,
                timestamp_ms=200.0,
                features={
                    "wrist_velocity": 10.0,
                    "elbow_angle": 110.0,
                },
            ),
        ],
        fps=30.0,
        feature_schema="full_body_temporal",
        feature_version="1.0.0",
    )


def test_builds_dataset_with_labels_and_metadata():
    records = [
        make_record(
            clip_id="clip_001",
            source_video_id="video_001",
            split="train",
            label="smash",
        ),
        make_record(
            clip_id="clip_002",
            source_video_id="video_002",
            split="test",
            label="clear",
        ),
    ]

    sequences = {
        "clip_001": make_temporal_sequence(),
        "clip_002": make_temporal_sequence(),
    }

    dataset = build_feature_dataset(
        records,
        sequences,
        target_length=4,
    )

    assert len(dataset.samples) == 2
    assert dataset.labels == ["smash", "clear"]
    assert dataset.splits == ["train", "test"]
    assert dataset.clip_ids == ["clip_001", "clip_002"]
    assert dataset.target_length == 4

    assert dataset.samples[0].source_video_id == "video_001"
    assert dataset.samples[1].source_video_id == "video_002"

    assert len(dataset.sequences[0]) == 4
    assert len(dataset.sequences[1]) == 4


def test_rejects_missing_temporal_sequence():
    records = [make_record()]

    with pytest.raises(ValueError, match="Missing temporal sequence"):
        build_feature_dataset(
            records,
            {},
        )


def test_rejects_source_video_leakage():
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

    sequences = {
        "clip_train": make_temporal_sequence(),
        "clip_test": make_temporal_sequence(),
    }

    with pytest.raises(ValueError, match="Source-video leakage"):
        build_feature_dataset(
            records,
            sequences,
        )


def test_can_disable_source_video_leakage_check():
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

    sequences = {
        "clip_train": make_temporal_sequence(),
        "clip_test": make_temporal_sequence(),
    }

    dataset = build_feature_dataset(
        records,
        sequences,
        reject_source_video_leakage=False,
    )

    assert len(dataset.samples) == 2


def test_rejects_inconsistent_feature_schema():
    records = [
        make_record(
            clip_id="clip_001",
            source_video_id="video_001",
        ),
        make_record(
            clip_id="clip_002",
            source_video_id="video_002",
        ),
    ]

    sequence_a = make_temporal_sequence()

    sequence_b = TemporalFeatureSequence(
        frames=[
            TemporalFeatureFrame(
                frame_index=0,
                timestamp_ms=0.0,
                features={"different_feature": 1.0},
            ),
            TemporalFeatureFrame(
                frame_index=1,
                timestamp_ms=100.0,
                features={"different_feature": 2.0},
            ),
        ],
        fps=30.0,
        feature_schema="full_body_temporal",
        feature_version="1.0.0",
    )

    with pytest.raises(ValueError, match="Feature schema mismatch"):
        build_feature_dataset(
            records,
            {
                "clip_001": sequence_a,
                "clip_002": sequence_b,
            },
        )


def test_rejects_unreviewed_record():
    record = make_record()

    record = DatasetRecord(
        **{
            **record.__dict__,
            "annotation_status": "unreviewed",
        }
    )

    with pytest.raises(ValueError, match="invalid manifest"):
        build_feature_dataset(
            [record],
            {"clip_001": make_temporal_sequence()},
        )