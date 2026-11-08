"""Structural validation for the SportsIQ annotation manifest."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

REQUIRED_COLUMNS = (
    "movement_id",
    "interval_id",
    "sequence_id",
    "video_id",
    "player_id",
    "racket_side",
    "start_frame",
    "end_frame",
    "movement_label",
    "label_source",
    "annotation_status",
    "contact_candidate_status",
    "contact_evidence",
    "feature_csv_path",
    "source_video_path",
    "camera_view",
    "annotator_id",
    "uncertainty_reason",
    "protocol_version",
    "notes",
)
ALWAYS_REQUIRED_COLUMNS = tuple(
    field for field in REQUIRED_COLUMNS
    if field not in {"contact_evidence", "uncertainty_reason", "notes"}
)

PHASE_LABELS = {
    "preparation",
    "backswing",
    "forward_swing",
    "follow_through",
    "recovery",
    "unknown",
}
RACKET_SIDES = {"left", "right", "unknown"}
ANNOTATION_STATUSES = {
    "unreviewed",
    "provisional",
    "second_reviewed",
    "adjudicated",
    "frozen",
    "rejected",
}
CONTACT_STATUSES = {
    "not_marked",
    "candidate",
    "verified_contact",
    "not_contact",
    "uncertain",
}
PROPOSED_LABEL_SOURCES = {
    "manual_video_review",
    "manual_video_and_shuttle_review",
    "consensus_review",
}
PROPOSED_UNCERTAINTY_REASONS = {
    "occlusion",
    "low_pose_confidence",
    "ambiguous_phase_boundary",
    "unclear_movement",
    "insufficient_video_context",
    "reviewer_disagreement",
    "other",
}
PROPOSED_CAMERA_VIEWS = {"side", "front", "rear", "diagonal", "unknown"}
FRAME_COLUMNS = ("frame_index", "timestamp_ms")


@dataclass(frozen=True)
class Diagnostic:
    severity: str
    row_number: int | None
    field: str | None
    message: str


@dataclass(frozen=True)
class ManifestValidationResult:
    diagnostics: tuple[Diagnostic, ...]
    row_count: int

    @property
    def valid(self) -> bool:
        return not any(item.severity == "error" for item in self.diagnostics)


@dataclass(frozen=True)
class ManifestValidationOptions:
    dataset_root: Path | None = None
    source_video_frame_counts: Mapping[str, int] | None = None
    check_paths: bool = True
    check_feature_coverage: bool = True
    split_by_video: Mapping[str, str] | None = None
    split_by_player: Mapping[str, str] | None = None
    split_assignments: Iterable[Mapping[str, str]] | None = None
    check_player_split_leakage: bool = False
    require_single_sequence_per_movement: bool = False


def _diagnostic(
    severity: str,
    row_number: int | None,
    field: str | None,
    message: str,
) -> Diagnostic:
    return Diagnostic(severity, row_number, field, message)


def _value(row: Mapping[str, str], field: str) -> str:
    return row.get(field, "").strip()


def _resolved_path(root: Path | None, value: str) -> tuple[Path, bool]:
    path = Path(value)
    if root is None:
        return path.resolve(strict=False), False
    resolved_root = root.resolve(strict=False)
    resolved_path = (resolved_root / path if not path.is_absolute() else path).resolve(
        strict=False
    )
    try:
        resolved_path.relative_to(resolved_root)
    except ValueError:
        return resolved_path, True
    return resolved_path, False


def _read_feature_frames(path: Path) -> set[int] | None:
    try:
        with path.open(newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            if "frame_index" not in (reader.fieldnames or []):
                return None
            frames: set[int] = set()
            for row in reader:
                try:
                    frames.add(int((row.get("frame_index") or "").strip()))
                except ValueError:
                    return None
            return frames
    except OSError:
        return None


def _check_required_columns(
    fieldnames: list[str] | None,
) -> list[Diagnostic]:
    if fieldnames is None:
        return [_diagnostic("error", None, None, "Manifest is missing a CSV header")]
    missing = [field for field in REQUIRED_COLUMNS if field not in fieldnames]
    if missing:
        return [_diagnostic(
            "error",
            None,
            None,
            f"Missing required columns: {', '.join(missing)}",
        )]
    return []


def _parse_frame(
    row: Mapping[str, str],
    row_number: int,
    field: str,
    diagnostics: list[Diagnostic],
) -> int | None:
    value = _value(row, field)
    if value == "":
        diagnostics.append(_diagnostic("error", row_number, field, "Required frame is empty"))
        return None
    try:
        frame = int(value)
    except ValueError:
        diagnostics.append(_diagnostic(
            "error", row_number, field, f"Frame must be an integer: {value!r}"
        ))
        return None
    if frame < 0:
        diagnostics.append(_diagnostic(
            "error", row_number, field, "Frame must be non-negative"
        ))
        return None
    return frame


def _check_row_fields(
    row: Mapping[str, str],
    row_number: int,
    diagnostics: list[Diagnostic],
) -> tuple[int | None, int | None]:
    for field in ALWAYS_REQUIRED_COLUMNS:
        if _value(row, field) == "":
            diagnostics.append(_diagnostic(
                "error", row_number, field, "Required field is empty"
            ))

    racket_side = _value(row, "racket_side")
    if racket_side and racket_side not in RACKET_SIDES:
        diagnostics.append(_diagnostic(
            "error", row_number, "racket_side",
            f"Unsupported racket side: {racket_side!r}",
        ))
    label = _value(row, "movement_label")
    if label and label not in PHASE_LABELS:
        diagnostics.append(_diagnostic(
            "error", row_number, "movement_label",
            f"Unsupported movement label: {label!r}",
        ))
    status = _value(row, "annotation_status")
    if status and status not in ANNOTATION_STATUSES:
        diagnostics.append(_diagnostic(
            "error", row_number, "annotation_status",
            f"Unsupported annotation status: {status!r}",
        ))
    contact_status = _value(row, "contact_candidate_status")
    if contact_status and contact_status not in CONTACT_STATUSES:
        diagnostics.append(_diagnostic(
            "error", row_number, "contact_candidate_status",
            f"Unsupported contact status: {contact_status!r}",
        ))
    label_source = _value(row, "label_source")
    if label_source and label_source not in PROPOSED_LABEL_SOURCES:
        diagnostics.append(_diagnostic(
            "warning", row_number, "label_source",
            f"Unresolved/proposed label source value: {label_source!r}",
        ))
    camera_view = _value(row, "camera_view")
    if camera_view and camera_view not in PROPOSED_CAMERA_VIEWS:
        diagnostics.append(_diagnostic(
            "warning", row_number, "camera_view",
            f"Unresolved/proposed camera view value: {camera_view!r}",
        ))
    uncertainty = _value(row, "uncertainty_reason")
    if uncertainty and uncertainty not in PROPOSED_UNCERTAINTY_REASONS:
        diagnostics.append(_diagnostic(
            "warning", row_number, "uncertainty_reason",
            f"Unresolved/proposed uncertainty reason: {uncertainty!r}",
        ))
    if label == "unknown" and not uncertainty:
        diagnostics.append(_diagnostic(
            "error", row_number, "uncertainty_reason",
            "unknown intervals require an uncertainty reason",
        ))
    if contact_status == "uncertain" and not uncertainty:
        diagnostics.append(_diagnostic(
            "error", row_number, "uncertainty_reason",
            "uncertain contact requires an uncertainty reason",
        ))

    evidence = _value(row, "contact_evidence")
    if contact_status in {"candidate", "verified_contact", "uncertain"} and not evidence:
        diagnostics.append(_diagnostic(
            "error", row_number, "contact_evidence",
            f"{contact_status} contact requires non-empty evidence",
        ))
    if contact_status in {"not_marked", "not_contact"} and evidence not in {"", "not_observed"}:
        diagnostics.append(_diagnostic(
            "warning", row_number, "contact_evidence",
            "Contact evidence is present although contact status is not active",
        ))
    if contact_status in {"not_marked", "not_contact"} and not evidence:
        diagnostics.append(_diagnostic(
            "warning", row_number, "contact_evidence",
            "Contact evidence is empty; not_observed semantics remain unresolved",
        ))
    if contact_status == "verified_contact":
        if label_source not in PROPOSED_LABEL_SOURCES:
            diagnostics.append(_diagnostic(
                "error", row_number, "label_source",
                "verified_contact requires an approved manual-review label source",
            ))
        if evidence in {"video_review_only", "unclear", "not_observed"}:
            diagnostics.append(_diagnostic(
                "warning", row_number, "contact_evidence",
                "Contact evidence is ambiguous and requires human semantic review",
            ))
    if contact_status == "verified_contact" and label == "unknown":
        diagnostics.append(_diagnostic(
            "warning", row_number, "movement_label",
            "Verified contact is an event marker; unknown remains an abstention label",
        ))

    start = _parse_frame(row, row_number, "start_frame", diagnostics)
    end = _parse_frame(row, row_number, "end_frame", diagnostics)
    if start is not None and end is not None and start > end:
        diagnostics.append(_diagnostic(
            "error", row_number, "start_frame",
            "start_frame must be less than or equal to end_frame",
        ))
    return start, end


def _check_relationships(
    rows: list[tuple[int, Mapping[str, str], int | None, int | None]],
    diagnostics: list[Diagnostic],
    options: ManifestValidationOptions,
) -> None:
    parent_values: dict[str, dict[str, str]] = {
        "movement_id": {},
        "sequence_id": {},
        "interval_id": {},
    }
    movement_videos: dict[str, str] = {}
    sequence_contexts: dict[str, tuple[str, str]] = {}
    seen_intervals: dict[tuple[str, int, int], int] = {}
    movement_intervals: dict[str, list[tuple[int, int, int]]] = {}
    for row_number, row, start, end in rows:
        movement = _value(row, "movement_id")
        sequence = _value(row, "sequence_id")
        interval = _value(row, "interval_id")
        video = _value(row, "video_id")
        for field, value in (
            ("movement_id", movement),
            ("sequence_id", sequence),
            ("interval_id", interval),
        ):
            if value and field == "interval_id" and value in parent_values[field]:
                diagnostics.append(_diagnostic(
                    "error", row_number, field,
                    f"Duplicate globally unique interval_id: {value!r}",
                ))
            elif value and field == "interval_id":
                parent_values[field][value] = movement
            elif value and field == "movement_id" and value not in parent_values[field]:
                parent_values[field][value] = video
            elif value and field == "sequence_id" and value not in parent_values[field]:
                parent_values[field][value] = video
        if movement and movement in movement_videos and movement_videos[movement] != video:
            diagnostics.append(_diagnostic(
                "error", row_number, "video_id",
                f"movement_id {movement!r} maps to multiple video_id values",
            ))
        elif movement:
            movement_videos[movement] = video
        context = (video, movement)
        if sequence and sequence in sequence_contexts and sequence_contexts[sequence] != context:
            diagnostics.append(_diagnostic(
                "error", row_number, "sequence_id",
                f"sequence_id {sequence!r} maps to multiple video/movement contexts",
            ))
        elif sequence:
            sequence_contexts[sequence] = context
        if interval and start is not None and end is not None:
            key = (movement, start, end)
            if key in seen_intervals:
                diagnostics.append(_diagnostic(
                    "error", row_number, "interval_id",
                    f"Duplicate interval range; first appears on row {seen_intervals[key]}",
                ))
            else:
                seen_intervals[key] = row_number
            movement_intervals.setdefault(movement, []).append((start, end, row_number))

    if options.require_single_sequence_per_movement:
        sequences_by_movement: dict[str, set[str]] = {}
        for _, row, _, _ in rows:
            sequences_by_movement.setdefault(
                _value(row, "movement_id"), set()
            ).add(_value(row, "sequence_id"))
        for movement, sequences in sequences_by_movement.items():
            if len(sequences) > 1:
                diagnostics.append(_diagnostic(
                    "error", None, "sequence_id",
                    f"Movement {movement!r} references multiple sequences; "
                    "strict single-sequence mode is enabled",
                ))

    for movement, intervals in movement_intervals.items():
        ordered = sorted(intervals, key=lambda item: (item[0], item[1], item[2]))
        for previous, current in zip(ordered, ordered[1:]):
            if current[0] <= previous[1]:
                diagnostics.append(_diagnostic(
                    "error", current[2], "start_frame",
                    f"Interval overlaps row {previous[2]} within movement {movement!r}; "
                    "endpoints are inclusive",
                ))

    protocol_versions = {
        _value(row, "protocol_version")
        for _, row, _, _ in rows
        if _value(row, "protocol_version")
    }
    if len(protocol_versions) > 1:
        diagnostics.append(_diagnostic(
            "error",
            None,
            "protocol_version",
            "Manifest rows must use one protocol_version",
        ))


def _check_external_data(
    rows: list[tuple[int, Mapping[str, str], int | None, int | None]],
    diagnostics: list[Diagnostic],
    options: ManifestValidationOptions,
) -> None:
    feature_cache: dict[Path, set[int] | None] = {}
    for row_number, row, start, end in rows:
        video_id = _value(row, "video_id")
        source_path, source_outside_root = _resolved_path(
            options.dataset_root,
            _value(row, "source_video_path"),
        )
        feature_path, feature_outside_root = _resolved_path(
            options.dataset_root,
            _value(row, "feature_csv_path"),
        )
        if source_outside_root:
            diagnostics.append(_diagnostic(
                "error", row_number, "source_video_path",
                "Source video path resolves outside dataset_root",
            ))
        if feature_outside_root:
            diagnostics.append(_diagnostic(
                "error", row_number, "feature_csv_path",
                "Feature CSV path resolves outside dataset_root",
            ))
        if options.check_paths:
            if not source_outside_root and not source_path.is_file():
                diagnostics.append(_diagnostic(
                    "warning", row_number, "source_video_path",
                    f"Source video is unavailable: {source_path}",
                ))
            if not feature_outside_root and not feature_path.is_file():
                diagnostics.append(_diagnostic(
                    "warning", row_number, "feature_csv_path",
                    f"Feature CSV is unavailable: {feature_path}",
                ))
        frame_count = (
            options.source_video_frame_counts.get(video_id)
            if options.source_video_frame_counts is not None
            else None
        )
        if frame_count is not None and end is not None and end >= frame_count:
            diagnostics.append(_diagnostic(
                "error", row_number, "end_frame",
                f"end_frame {end} is outside source video with {frame_count} frames",
            ))
        if (
            options.check_feature_coverage
            and start is not None
            and end is not None
            and not feature_outside_root
            and feature_path.is_file()
        ):
            if feature_path not in feature_cache:
                feature_cache[feature_path] = _read_feature_frames(feature_path)
            frames = feature_cache[feature_path]
            if frames is None:
                diagnostics.append(_diagnostic(
                    "warning", row_number, "feature_csv_path",
                    "Feature CSV cannot be read with a valid frame_index column",
                ))
            else:
                missing = [
                    frame for frame in range(start, end + 1)
                    if frame not in frames
                ]
                if missing:
                    diagnostics.append(_diagnostic(
                        "error", row_number, "feature_csv_path",
                        f"Feature CSV is missing {len(missing)} interval frame(s)",
                    ))


def _check_splits(
    rows: list[tuple[int, Mapping[str, str], int | None, int | None]],
    diagnostics: list[Diagnostic],
    options: ManifestValidationOptions,
) -> None:
    assignments: list[tuple[str, str, str | None, int | None]] = []
    if options.split_assignments is not None:
        for index, assignment in enumerate(options.split_assignments, start=1):
            video_id = assignment.get("video_id", "").strip()
            split = assignment.get("split", "").strip()
            player_id = assignment.get("player_id", "").strip() or None
            if not video_id or not split:
                diagnostics.append(_diagnostic(
                    "error", None, None,
                    f"Split assignment {index} requires video_id and split",
                ))
                continue
            assignments.append((video_id, split, player_id, None))
    for video_id, split in (options.split_by_video or {}).items():
        assignments.append((video_id, split, None, None))
    for player_id, split in (options.split_by_player or {}).items():
        assignments.append(("", split, player_id, None))

    videos: dict[str, set[str]] = {}
    players: dict[str, set[str]] = {}
    for video_id, split, player_id, row_number in assignments:
        if video_id:
            videos.setdefault(video_id, set()).add(split)
        if player_id is not None:
            players.setdefault(player_id, set()).add(split)
    for video_id, splits in sorted(videos.items()):
        if len(splits) > 1:
            diagnostics.append(_diagnostic(
                "error", None, "video_id",
                f"video_id {video_id!r} appears in multiple splits: "
                f"{', '.join(sorted(splits))}",
            ))
    if options.check_player_split_leakage:
        for player_id, splits in sorted(players.items()):
            if len(splits) > 1:
                diagnostics.append(_diagnostic(
                    "error", None, "player_id",
                    f"player_id {player_id!r} appears in multiple splits: "
                    f"{', '.join(sorted(splits))}",
                ))


def validate_rows(
    fieldnames: list[str] | None,
    rows: Iterable[Mapping[str, str]],
    options: ManifestValidationOptions | None = None,
) -> ManifestValidationResult:
    """Validate manifest rows and return deterministic structured diagnostics."""
    options = options or ManifestValidationOptions()
    diagnostics = _check_required_columns(fieldnames)
    if diagnostics:
        return ManifestValidationResult(tuple(diagnostics), 0)
    materialized = list(rows)
    if not materialized:
        return ManifestValidationResult((
            _diagnostic("error", None, None, "Manifest contains no data rows"),
        ), 0)

    parsed: list[tuple[int, Mapping[str, str], int | None, int | None]] = []
    for index, row in enumerate(materialized, start=2):
        if None in row:
            diagnostics.append(_diagnostic(
                "error",
                index,
                None,
                "Malformed CSV row contains more fields than the header",
            ))
        start, end = _check_row_fields(row, index, diagnostics)
        parsed.append((index, row, start, end))
    _check_relationships(parsed, diagnostics, options)
    _check_external_data(parsed, diagnostics, options)
    _check_splits(parsed, diagnostics, options)
    diagnostics.sort(key=lambda item: (
        item.row_number is None,
        item.row_number or 0,
        item.field or "",
        item.severity,
        item.message,
    ))
    return ManifestValidationResult(tuple(diagnostics), len(materialized))


def validate_manifest(
    manifest_path: Path,
    options: ManifestValidationOptions | None = None,
) -> ManifestValidationResult:
    """Read and validate a CSV manifest without discarding malformed rows."""
    try:
        with manifest_path.open(newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            return validate_rows(reader.fieldnames, reader, options)
    except OSError as error:
        return ManifestValidationResult((
            _diagnostic("error", None, None, f"Cannot read manifest: {error}"),
        ), 0)
