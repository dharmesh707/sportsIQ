"""Dataset manifest orchestration for offline full-body feature extraction."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from app.ml.dataset.builder import (
    BuiltFeatureDataset,
    build_feature_dataset,
)
from app.ml.dataset.io import read_manifest_csv
from app.ml.dataset.manifest import (
    DatasetRecord,
    audit_split_leakage,
    resolve_clip_path,
    validate_manifest,
)
from app.ml.features.full_body import preprocess_full_body_sequence
from app.ml.features.full_body_temporal import (
    TemporalFeatureSequence,
    extract_full_body_temporal_features,
)
from app.ml.features.joint_angles import extract_joint_angles
from app.ml.pose.canonical_slicing import slice_canonical_pose_sequence
from app.ml.pose.full_body_sequence import extract_full_body_pose_sequence


@dataclass(frozen=True)
class DatasetExtractionDiagnostics:
    """Source-video and clip accounting for one dataset-building run."""

    source_video_count: int
    clip_count: int
    source_video_ids: tuple[str, ...]
    extracted_frame_counts: dict[str, int]
    clip_frame_counts: dict[str, int]


@dataclass(frozen=True)
class DatasetExtractionResult:
    """Built fixed-length dataset plus extraction diagnostics."""

    dataset: BuiltFeatureDataset
    diagnostics: DatasetExtractionDiagnostics


def _read_records(
    manifest: str | Path | Iterable[DatasetRecord],
) -> list[DatasetRecord]:
    if isinstance(manifest, (str, Path)):
        return read_manifest_csv(manifest)
    return list(manifest)


def _validate_records(records: list[DatasetRecord]) -> None:
    validation = validate_manifest(records)
    if not validation.valid:
        raise ValueError(
            "Cannot build dataset from invalid manifest:\n"
            + "\n".join(validation.errors)
        )

    leakage = audit_split_leakage(records)
    if leakage.has_source_video_leakage:
        details = "; ".join(
            f"{video_id}: {splits}"
            for video_id, splits in leakage.source_video_leakage.items()
        )
        raise ValueError(
            "Source-video leakage detected across dataset splits: "
            + details
        )


def _group_source_videos(
    records: list[DatasetRecord],
    dataset_root: str | Path,
) -> dict[str, Path]:
    paths_by_source: dict[str, Path] = {}
    for record in records:
        resolved_path = resolve_clip_path(dataset_root, record.clip_path)
        existing_path = paths_by_source.get(record.source_video_id)
        if existing_path is not None and existing_path != resolved_path:
            raise ValueError(
                "source_video_id maps to multiple clip paths: "
                f"{record.source_video_id!r} maps to "
                f"{existing_path} and {resolved_path}"
            )
        paths_by_source[record.source_video_id] = resolved_path
    return paths_by_source


def build_dataset_from_manifest(
    manifest: str | Path | Iterable[DatasetRecord],
    *,
    dataset_root: str | Path,
    target_length: int = 32,
    confidence_threshold: float = 0.5,
    reject_source_video_leakage: bool = True,
) -> DatasetExtractionResult:
    """Extract each source video once and build its annotated clip dataset.

    Annotation intervals use the existing start-inclusive/end-exclusive
    timestamp slicing contract. Raw frame indices and timestamps are retained
    in every sliced sequence.
    """
    records = _read_records(manifest)
    _validate_records(records)

    if not reject_source_video_leakage:
        # The manifest is still checked above because source-video grouping is
        # unsafe when records from one recording cross dataset splits.
        raise ValueError(
            "Source-video leakage cannot be disabled for dataset orchestration."
        )

    paths_by_source = _group_source_videos(records, dataset_root)
    source_sequences = {}
    extracted_frame_counts: dict[str, int] = {}

    for source_video_id, video_path in paths_by_source.items():
        try:
            sequence = extract_full_body_pose_sequence(video_path)
        except Exception as error:
            raise RuntimeError(
                f"Failed to extract source video "
                f"{source_video_id!r} from {video_path}: {error}"
            ) from error
        source_sequences[source_video_id] = sequence
        extracted_frame_counts[source_video_id] = len(sequence.frames)

    temporal_by_clip: dict[str, TemporalFeatureSequence] = {}
    clip_frame_counts: dict[str, int] = {}

    for record in records:
        source_sequence = source_sequences[record.source_video_id]
        clip_sequence = slice_canonical_pose_sequence(
            source_sequence,
            start_ms=record.start_ms,
            end_ms=record.end_ms,
        )
        frame_count = len(clip_sequence.frames)
        if frame_count == 0:
            raise ValueError(
                f"Annotation interval for clip_id {record.clip_id!r} "
                f"contains no source frames: "
                f"[{record.start_ms}, {record.end_ms}) ms."
            )
        if frame_count < 2:
            raise ValueError(
                f"Annotation interval for clip_id {record.clip_id!r} "
                "must contain at least two source frames for temporal "
                f"features; found {frame_count}."
            )
        clip_frame_counts[record.clip_id] = frame_count

        position_sequence = preprocess_full_body_sequence(
            clip_sequence,
            confidence_threshold=confidence_threshold,
        )
        angle_sequence = extract_joint_angles(
            clip_sequence,
            confidence_threshold=confidence_threshold,
        )
        temporal_by_clip[record.clip_id] = (
            extract_full_body_temporal_features(
                position_sequence,
                angle_sequence,
            )
        )

    dataset = build_feature_dataset(
        records,
        temporal_by_clip,
        target_length=target_length,
        reject_source_video_leakage=reject_source_video_leakage,
    )
    diagnostics = DatasetExtractionDiagnostics(
        source_video_count=len(paths_by_source),
        clip_count=len(records),
        source_video_ids=tuple(paths_by_source),
        extracted_frame_counts=extracted_frame_counts,
        clip_frame_counts=clip_frame_counts,
    )
    return DatasetExtractionResult(dataset=dataset, diagnostics=diagnostics)
