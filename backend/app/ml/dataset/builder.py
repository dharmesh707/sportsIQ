from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.ml.dataset.manifest import (
    DatasetRecord,
    audit_split_leakage,
    validate_manifest,
)
from app.ml.features.full_body_temporal import TemporalFeatureSequence
from app.ml.features.sequence_encoder import (
    EncodedTemporalSequence,
    encode_temporal_sequence,
)


@dataclass(frozen=True)
class DatasetFeatureSample:
    """
    One encoded action sample plus its label and provenance metadata.
    """

    clip_id: str
    label: str
    source_video_id: str
    player_id: str
    session_id: str
    split: str
    start_ms: float
    end_ms: float
    encoded_sequence: EncodedTemporalSequence


@dataclass(frozen=True)
class BuiltFeatureDataset:
    """
    Dataset built from reviewed manifest records and temporal sequences.
    """

    samples: list[DatasetFeatureSample]
    feature_names: list[str]
    target_length: int
    feature_schema: str
    feature_version: str

    @property
    def labels(self) -> list[str]:
        return [sample.label for sample in self.samples]

    @property
    def splits(self) -> list[str]:
        return [sample.split for sample in self.samples]

    @property
    def clip_ids(self) -> list[str]:
        return [sample.clip_id for sample in self.samples]

    @property
    def source_video_ids(self) -> list[str]:
        return [sample.source_video_id for sample in self.samples]

    @property
    def players(self) -> list[str]:
        return [sample.player_id for sample in self.samples]

    @property
    def sequences(self) -> list[list[list[Optional[float]]]]:
        return [
            sample.encoded_sequence.values
            for sample in self.samples
        ]


def build_feature_dataset(
    records: list[DatasetRecord],
    sequences_by_clip_id: dict[str, TemporalFeatureSequence],
    *,
    target_length: int = 32,
    reject_source_video_leakage: bool = True,
) -> BuiltFeatureDataset:
    """
    Build a fixed-length feature dataset from manifest records.

    Only reviewed records are accepted by manifest validation.

    Every manifest record must have a matching temporal sequence.
    Extra sequences not referenced by the manifest are ignored.

    By default, rejects source videos appearing across multiple splits.
    This prevents windows from the same original recording from leaking
    between training, validation, and test datasets.
    """
    if not records:
        raise ValueError("Cannot build a dataset from an empty manifest.")

    validation = validate_manifest(records)

    if not validation.valid:
        raise ValueError(
            "Cannot build dataset from invalid manifest:\n"
            + "\n".join(validation.errors)
        )

    if target_length < 1:
        raise ValueError("target_length must be at least 1.")

    if reject_source_video_leakage:
        leakage = audit_split_leakage(records)

        if leakage.has_source_video_leakage:
            details = "; ".join(
                f"{video_id}: {splits}"
                for video_id, splits in (
                    leakage.source_video_leakage.items()
                )
            )

            raise ValueError(
                "Source-video leakage detected across dataset splits: "
                + details
            )

    samples: list[DatasetFeatureSample] = []
    expected_feature_names: Optional[list[str]] = None

    for record in records:
        temporal_sequence = sequences_by_clip_id.get(record.clip_id)

        if temporal_sequence is None:
            raise ValueError(
                "Missing temporal sequence for clip_id "
                f"{record.clip_id!r}."
            )

        encoded = encode_temporal_sequence(
            temporal_sequence,
            target_length=target_length,
        )

        if expected_feature_names is None:
            expected_feature_names = encoded.feature_names
        elif encoded.feature_names != expected_feature_names:
            raise ValueError(
                "Feature schema mismatch for clip_id "
                f"{record.clip_id!r}. "
                "All encoded samples must have identical feature names "
                "and order."
            )

        samples.append(
            DatasetFeatureSample(
                clip_id=record.clip_id,
                label=record.stroke_label,
                source_video_id=record.source_video_id,
                player_id=record.player_id,
                session_id=record.session_id,
                split=record.split,
                start_ms=record.start_ms,
                end_ms=record.end_ms,
                encoded_sequence=encoded,
            )
        )

    assert expected_feature_names is not None

    return BuiltFeatureDataset(
        samples=samples,
        feature_names=expected_feature_names,
        target_length=target_length,
        feature_schema="sportsiq_feature_dataset",
        feature_version="1.0.0",
    )