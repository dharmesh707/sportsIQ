from types import SimpleNamespace

import pytest

from app.ml.dataset.manifest import DatasetRecord
from app.ml.dataset.orchestration import build_dataset_from_manifest
from app.ml.features.full_body_temporal import (
    TemporalFeatureFrame,
    TemporalFeatureSequence,
)
from app.ml.pose.canonical import CanonicalPoseSequence


def _record(
    clip_id,
    source_video_id="video-1",
    clip_path="videos/source.mp4",
    split="train",
    start_ms=0.0,
    end_ms=100.0,
    label="smash",
):
    return DatasetRecord(
        clip_id=clip_id,
        clip_path=clip_path,
        stroke_label=label,
        source_video_id=source_video_id,
        player_id="player-1",
        session_id="session-1",
        start_ms=start_ms,
        end_ms=end_ms,
        split=split,
        annotation_status="reviewed",
    )


def _canonical_sequence(frame_count=4):
    return CanonicalPoseSequence(
        frames=tuple(),
        estimator_name="test",
        estimator_version=None,
        model_name=None,
        fps=30.0,
    )


def _temporal_sequence(marker):
    return TemporalFeatureSequence(
        frames=[
            TemporalFeatureFrame(
                frame_index=marker,
                timestamp_ms=0.0,
                features={"marker": float(marker)},
            ),
            TemporalFeatureFrame(
                frame_index=marker + 1,
                timestamp_ms=100.0,
                features={"marker": float(marker)},
            ),
        ],
        fps=30.0,
        feature_schema="full_body_temporal",
        feature_version="1.0.0",
    )


def _patch_pipeline(monkeypatch, *, slice_fn=None):
    import app.ml.dataset.orchestration as pipeline

    calls = []

    monkeypatch.setattr(
        pipeline,
        "extract_full_body_pose_sequence",
        lambda path: calls.append(path) or _canonical_sequence(),
    )
    monkeypatch.setattr(
        pipeline,
        "preprocess_full_body_sequence",
        lambda sequence, confidence_threshold: sequence,
    )
    monkeypatch.setattr(
        pipeline,
        "extract_joint_angles",
        lambda sequence, confidence_threshold: sequence,
    )
    monkeypatch.setattr(
        pipeline,
        "extract_full_body_temporal_features",
        lambda position, angles: _temporal_sequence(
            len(position.frames)
        ),
    )
    if slice_fn is not None:
        monkeypatch.setattr(pipeline, "slice_canonical_pose_sequence", slice_fn)
    return calls


def test_extracts_one_source_and_slices_each_annotation(monkeypatch, tmp_path):
    records = [
        _record("clip-a", start_ms=0.0, end_ms=100.0),
        _record("clip-b", start_ms=100.0, end_ms=200.0),
    ]
    slices = []

    def slice_fn(sequence, start_ms, end_ms):
        slices.append((start_ms, end_ms))
        return SimpleNamespace(frames=(object(), object()))

    calls = _patch_pipeline(monkeypatch, slice_fn=slice_fn)
    result = build_dataset_from_manifest(records, dataset_root=tmp_path)

    assert calls == [tmp_path / "videos" / "source.mp4"]
    assert slices == [(0.0, 100.0), (100.0, 200.0)]
    assert result.diagnostics.source_video_count == 1
    assert result.diagnostics.clip_frame_counts == {"clip-a": 2, "clip-b": 2}


def test_each_clip_gets_its_own_temporal_sequence(monkeypatch, tmp_path):
    records = [
        _record("clip-a"),
        _record("clip-b", start_ms=100.0, end_ms=200.0),
    ]
    temporal_markers = []
    _patch_pipeline(monkeypatch, slice_fn=lambda sequence, start_ms, end_ms:
                    SimpleNamespace(frames=(object(), object())))

    import app.ml.dataset.orchestration as pipeline

    monkeypatch.setattr(
        pipeline,
        "extract_full_body_temporal_features",
        lambda position, angles: (
            temporal_markers.append(id(position)) or _temporal_sequence(
                len(temporal_markers)
            )
        ),
    )

    result = build_dataset_from_manifest(records, dataset_root=tmp_path)

    assert len(temporal_markers) == 2
    assert result.dataset.clip_ids == ["clip-a", "clip-b"]
    assert result.dataset.labels == ["smash", "smash"]


def test_source_video_leakage_is_rejected_before_extraction(monkeypatch, tmp_path):
    records = [
        _record("clip-train", split="train"),
        _record("clip-test", split="test"),
    ]
    calls = []
    monkeypatch.setattr(
        "app.ml.dataset.orchestration.extract_full_body_pose_sequence",
        lambda path: calls.append(path),
    )

    with pytest.raises(ValueError, match="Source-video leakage"):
        build_dataset_from_manifest(records, dataset_root=tmp_path)

    assert calls == []


def test_empty_annotation_window_has_explicit_error(monkeypatch, tmp_path):
    records = [_record("empty", start_ms=500.0, end_ms=600.0)]
    _patch_pipeline(
        monkeypatch,
        slice_fn=lambda sequence, start_ms, end_ms:
        SimpleNamespace(frames=()),
    )

    with pytest.raises(ValueError, match="contains no source frames"):
        build_dataset_from_manifest(records, dataset_root=tmp_path)


def test_source_extraction_failure_identifies_video_and_path(monkeypatch, tmp_path):
    records = [_record("clip-a")]
    import app.ml.dataset.orchestration as pipeline

    monkeypatch.setattr(
        pipeline,
        "extract_full_body_pose_sequence",
        lambda path: (_ for _ in ()).throw(RuntimeError("decoder failed")),
    )

    with pytest.raises(RuntimeError, match="video-1.*videos.source.mp4.*decoder failed"):
        build_dataset_from_manifest(records, dataset_root=tmp_path)


def test_dataset_contains_manifest_metadata(monkeypatch, tmp_path):
    records = [
        _record("clip-a", label="smash"),
        _record(
            "clip-b",
            source_video_id="video-2",
            clip_path="videos/other.mp4",
            label="clear",
        ),
    ]
    _patch_pipeline(
        monkeypatch,
        slice_fn=lambda sequence, start_ms, end_ms:
        SimpleNamespace(frames=(object(), object())),
    )

    result = build_dataset_from_manifest(records, dataset_root=tmp_path)

    assert result.dataset.clip_ids == ["clip-a", "clip-b"]
    assert result.dataset.labels == ["smash", "clear"]
    assert result.dataset.source_video_ids == ["video-1", "video-2"]
    assert result.dataset.splits == ["train", "train"]
    assert result.dataset.samples[0].start_ms == 0.0
    assert result.dataset.samples[1].end_ms == 100.0
