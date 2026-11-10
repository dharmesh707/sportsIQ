from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional


VALID_SPLITS = {"train", "validation", "test"}


@dataclass(frozen=True)
class DatasetRecord:
    """
    Metadata describing one annotated badminton action clip.

    clip_path should be a path relative to the dataset root where possible.
    source_video_id identifies the original recording.
    player_id and session_id support group-aware evaluation.
    """

    clip_id: str
    clip_path: str
    stroke_label: str
    source_video_id: str
    player_id: str
    session_id: str
    start_ms: float
    end_ms: float
    split: str
    annotation_status: str = "reviewed"
    reviewer_id: Optional[str] = None


@dataclass(frozen=True)
class ManifestValidationResult:
    valid: bool
    errors: list[str]


@dataclass(frozen=True)
class LeakageReport:
    """
    Reports groups appearing in more than one dataset split.
    """

    source_video_leakage: dict[str, list[str]]
    player_leakage: dict[str, list[str]]

    @property
    def has_source_video_leakage(self) -> bool:
        return bool(self.source_video_leakage)

    @property
    def has_player_leakage(self) -> bool:
        return bool(self.player_leakage)

    @property
    def has_any_leakage(self) -> bool:
        return (
            self.has_source_video_leakage
            or self.has_player_leakage
        )


def validate_dataset_record(
    record: DatasetRecord,
) -> ManifestValidationResult:
    """
    Validate required dataset metadata and clip timing.
    """
    errors: list[str] = []

    required_fields = {
        "clip_id": record.clip_id,
        "clip_path": record.clip_path,
        "stroke_label": record.stroke_label,
        "source_video_id": record.source_video_id,
        "player_id": record.player_id,
        "session_id": record.session_id,
    }

    for field_name, value in required_fields.items():
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{field_name} must be a non-empty string.")

    if record.split not in VALID_SPLITS:
        errors.append(
            f"split must be one of {sorted(VALID_SPLITS)}."
        )

    if record.annotation_status not in {"reviewed", "unreviewed"}:
        errors.append(
            "annotation_status must be 'reviewed' or 'unreviewed'."
        )

    if record.annotation_status != "reviewed":
        errors.append(
            "Only reviewed annotations are eligible for the training dataset."
        )

    if record.start_ms < 0:
        errors.append("start_ms must be non-negative.")

    if record.end_ms <= record.start_ms:
        errors.append("end_ms must be greater than start_ms.")

    return ManifestValidationResult(
        valid=not errors,
        errors=errors,
    )


def validate_manifest(
    records: Iterable[DatasetRecord],
) -> ManifestValidationResult:
    """
    Validate every record and enforce unique clip IDs.
    """
    errors: list[str] = []
    seen_clip_ids: set[str] = set()

    for record in records:
        result = validate_dataset_record(record)
        errors.extend(
            f"{record.clip_id}: {error}"
            for error in result.errors
        )

        if record.clip_id in seen_clip_ids:
            errors.append(
                f"Duplicate clip_id: {record.clip_id}."
            )

        seen_clip_ids.add(record.clip_id)

    return ManifestValidationResult(
        valid=not errors,
        errors=errors,
    )


def audit_split_leakage(
    records: Iterable[DatasetRecord],
) -> LeakageReport:
    """
    Identify source videos or players appearing across multiple splits.

    Source-video leakage is generally a strict error for action
    recognition evaluation.

    Player overlap may be acceptable for some evaluation designs, but
    a player-disjoint test split is useful when measuring generalization
    to unseen players.
    """
    source_video_splits: dict[str, set[str]] = {}
    player_splits: dict[str, set[str]] = {}

    for record in records:
        source_video_splits.setdefault(
            record.source_video_id,
            set(),
        ).add(record.split)

        player_splits.setdefault(
            record.player_id,
            set(),
        ).add(record.split)

    source_video_leakage = {
        source_video_id: sorted(splits)
        for source_video_id, splits in source_video_splits.items()
        if len(splits) > 1
    }

    player_leakage = {
        player_id: sorted(splits)
        for player_id, splits in player_splits.items()
        if len(splits) > 1
    }

    return LeakageReport(
        source_video_leakage=source_video_leakage,
        player_leakage=player_leakage,
    )


def resolve_clip_path(
    dataset_root: str | Path,
    clip_path: str,
) -> Path:
    """
    Resolve a clip path beneath a dataset root.

    Rejects paths that escape the dataset root.
    """
    root = Path(dataset_root).resolve()
    resolved_path = (root / clip_path).resolve()

    try:
        resolved_path.relative_to(root)
    except ValueError as exc:
        raise ValueError(
            "clip_path must remain inside the dataset root."
        ) from exc

    return resolved_path