import csv
import sys

import pytest
from app.ml.dataset.manifest_validator import (
    REQUIRED_COLUMNS,
    ManifestValidationOptions,
    validate_rows,
)
from app.ml.scripts.validate_annotation_manifest import main


def _row(**overrides: str) -> dict[str, str]:
    row = {field: "" for field in REQUIRED_COLUMNS}
    row.update({
        "movement_id": "movement-1",
        "interval_id": "interval-1",
        "sequence_id": "sequence-1",
        "video_id": "video-1",
        "player_id": "player-1",
        "racket_side": "right",
        "start_frame": "0",
        "end_frame": "2",
        "movement_label": "preparation",
        "label_source": "manual_video_review",
        "annotation_status": "provisional",
        "contact_candidate_status": "not_marked",
        "contact_evidence": "not_observed",
        "feature_csv_path": "features.csv",
        "source_video_path": "video.mp4",
        "camera_view": "side",
        "annotator_id": "reviewer-1",
        "protocol_version": "v0.1",
    })
    row.update(overrides)
    return row


def _validate(*rows: dict[str, str], **kwargs):
    return validate_rows(list(REQUIRED_COLUMNS), rows, **kwargs)


def test_valid_manifest_allows_adjacent_intervals_and_gaps():
    first = _row(interval_id="interval-1", start_frame="0", end_frame="2")
    second = _row(
        interval_id="interval-2",
        start_frame="4",
        end_frame="5",
        movement_label="unknown",
        uncertainty_reason="insufficient_video_context",
    )

    result = _validate(first, second, options=ManifestValidationOptions(check_paths=False))

    assert result.valid
    assert not result.diagnostics


def test_valid_manifest_allows_exact_adjacent_intervals():
    first = _row(interval_id="interval-1", start_frame="0", end_frame="2")
    second = _row(interval_id="interval-2", start_frame="3", end_frame="5")

    result = _validate(first, second, options=ManifestValidationOptions(check_paths=False))

    assert result.valid
    assert result.diagnostics == ()


def test_missing_columns_and_empty_manifest_are_errors():
    missing = validate_rows(["movement_id"], [])
    empty = validate_rows(list(REQUIRED_COLUMNS), [])

    assert "Missing required columns" in missing.diagnostics[0].message
    assert "no data rows" in empty.diagnostics[0].message


def test_extra_csv_fields_are_reported_as_malformed():
    row = _row()
    row[None] = ["unexpected"]

    result = _validate(row, options=ManifestValidationOptions(check_paths=False))

    assert not result.valid
    assert any("more fields than the header" in item.message
               for item in result.diagnostics)


def test_rejects_bad_ids_relationships_and_overlap():
    first = _row()
    second = _row(
        interval_id="interval-2",
        start_frame="2",
        end_frame="4",
        movement_label="backswing",
        video_id="video-2",
    )

    result = _validate(
        first,
        second,
        options=ManifestValidationOptions(check_paths=False),
    )
    messages = [item.message for item in result.diagnostics]

    assert not result.valid
    assert any("multiple video_id" in message for message in messages)
    assert any("overlaps" in message for message in messages)


def test_rejects_duplicate_interval_id_and_duplicate_range():
    duplicate_id = _validate(
        _row(interval_id="same"),
        _row(interval_id="same", start_frame="3", end_frame="5"),
        options=ManifestValidationOptions(check_paths=False),
    )
    duplicate_range = _validate(
        _row(interval_id="first"),
        _row(interval_id="second"),
        options=ManifestValidationOptions(check_paths=False),
    )

    assert any(
        item.severity == "error"
        and item.field == "interval_id"
        and "Duplicate globally unique interval_id" in item.message
        for item in duplicate_id.diagnostics
    )
    assert any(
        item.severity == "error"
        and item.field == "interval_id"
        and "Duplicate interval range" in item.message
        for item in duplicate_range.diagnostics
    )


def test_rejects_sequence_mapped_to_multiple_movement_contexts():
    result = _validate(
        _row(),
        _row(
            interval_id="interval-2",
            movement_id="movement-2",
            start_frame="3",
            end_frame="5",
        ),
        options=ManifestValidationOptions(check_paths=False),
    )

    assert any(
        item.severity == "error"
        and item.field == "sequence_id"
        and "multiple video/movement contexts" in item.message
        for item in result.diagnostics
    )


def test_strict_single_sequence_mode_rejects_multiple_sequences():
    result = _validate(
        _row(),
        _row(
            interval_id="interval-2",
            sequence_id="sequence-2",
            start_frame="3",
            end_frame="5",
        ),
        options=ManifestValidationOptions(
            check_paths=False,
            require_single_sequence_per_movement=True,
        ),
    )

    assert any(
        item.severity == "error"
        and item.field == "sequence_id"
        and "strict single-sequence mode" in item.message
        for item in result.diagnostics
    )


def test_mixed_protocol_versions_are_rejected():
    result = _validate(
        _row(),
        _row(
            interval_id="interval-2",
            start_frame="3",
            end_frame="5",
            protocol_version="v0.2",
        ),
        options=ManifestValidationOptions(check_paths=False),
    )

    assert any(
        item.severity == "error"
        and item.field == "protocol_version"
        and "one protocol_version" in item.message
        for item in result.diagnostics
    )


def test_rejects_invalid_frames_labels_and_unknown_without_reason():
    result = _validate(_row(
        start_frame="x",
        end_frame="-1",
        movement_label="contact",
        annotation_status="draft",
        uncertainty_reason="",
    ), options=ManifestValidationOptions(check_paths=False))
    messages = [item.message for item in result.diagnostics]

    assert not result.valid
    assert any("must be an integer" in message for message in messages)
    assert any("non-negative" in message for message in messages)
    assert any("Unsupported movement label" in message for message in messages)
    assert any("Unsupported annotation status" in message for message in messages)


def test_contact_ambiguity_is_structural_error_only_for_missing_evidence():
    candidate = _row(
        contact_candidate_status="candidate",
        contact_evidence="",
    )
    vague = _row(
        interval_id="interval-2",
        contact_candidate_status="candidate",
        contact_evidence="video_review_only",
    )

    result = _validate(
        candidate,
        vague,
        options=ManifestValidationOptions(check_paths=False),
    )
    assert not result.valid
    assert any("requires non-empty evidence" in item.message for item in result.diagnostics)
    assert not any("video_review_only" in item.message and item.severity == "error"
                   for item in result.diagnostics)


def test_contact_validation_distinguishes_valid_invalid_and_ambiguous():
    valid = _validate(
        _row(
            contact_candidate_status="verified_contact",
            contact_evidence="racket_shuttle_interaction_visible",
        ),
        options=ManifestValidationOptions(check_paths=False),
    )
    invalid = _validate(
        _row(
            contact_candidate_status="verified_contact",
            contact_evidence="shuttle_visible",
            label_source="model",
        ),
        options=ManifestValidationOptions(check_paths=False),
    )
    ambiguous = _validate(
        _row(
            contact_candidate_status="verified_contact",
            contact_evidence="video_review_only",
        ),
        options=ManifestValidationOptions(check_paths=False),
    )

    assert valid.valid
    assert any(
        item.severity == "error"
        and item.field == "label_source"
        and "approved manual-review" in item.message
        for item in invalid.diagnostics
    )
    assert ambiguous.valid
    assert any(
        item.severity == "warning"
        and item.field == "contact_evidence"
        and "ambiguous" in item.message
        for item in ambiguous.diagnostics
    )


def test_feature_coverage_and_source_video_bounds(tmp_path):
    feature_path = tmp_path / "features.csv"
    with feature_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["frame_index", "timestamp_ms"])
        writer.writeheader()
        writer.writerows({"frame_index": str(index), "timestamp_ms": str(index)}
                         for index in (0, 1, 2))
    row = _row(
        feature_csv_path="features.csv",
        start_frame="0",
        end_frame="3",
    )
    result = _validate(
        row,
        options=ManifestValidationOptions(
            dataset_root=tmp_path,
            source_video_frame_counts={"video-1": 3},
        ),
    )

    assert not result.valid
    assert any("outside source video" in item.message for item in result.diagnostics)
    assert any("missing 1 interval frame" in item.message for item in result.diagnostics)


def test_split_leakage_is_detected_from_row_level_assignments():
    result = _validate(
        _row(),
        options=ManifestValidationOptions(
            check_paths=False,
            split_assignments=(
                {"video_id": "video-1", "split": "train"},
                {"video_id": "video-1", "split": "test"},
            ),
        ),
    )

    assert any(
        item.severity == "error"
        and item.field == "video_id"
        and "multiple splits" in item.message
        for item in result.diagnostics
    )


def test_player_split_leakage_is_optional():
    assignments = (
        {"video_id": "video-1", "player_id": "player-1", "split": "train"},
        {"video_id": "video-2", "player_id": "player-1", "split": "test"},
    )
    disabled = _validate(
        _row(),
        options=ManifestValidationOptions(
            check_paths=False,
            split_assignments=assignments,
        ),
    )
    enabled = _validate(
        _row(),
        options=ManifestValidationOptions(
            check_paths=False,
            split_assignments=assignments,
            check_player_split_leakage=True,
        ),
    )

    assert disabled.valid
    assert any(
        item.severity == "error"
        and item.field == "player_id"
        and "multiple splits" in item.message
        for item in enabled.diagnostics
    )


def test_path_containment_and_missing_relative_paths(tmp_path):
    feature_path = tmp_path / "features.csv"
    video_path = tmp_path / "video.mp4"
    with feature_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["frame_index"])
        writer.writeheader()
        writer.writerows({"frame_index": str(index)} for index in (0, 1, 2))
    video_path.touch()

    valid = _validate(
        _row(),
        options=ManifestValidationOptions(dataset_root=tmp_path),
    )
    missing = _validate(
        _row(feature_csv_path="missing.csv", source_video_path="missing.mp4"),
        options=ManifestValidationOptions(dataset_root=tmp_path),
    )
    traversal = _validate(
        _row(feature_csv_path="..\\outside.csv"),
        options=ManifestValidationOptions(dataset_root=tmp_path),
    )
    outside = _validate(
        _row(feature_csv_path=str(tmp_path.parent / "outside.csv")),
        options=ManifestValidationOptions(dataset_root=tmp_path),
    )

    assert valid.valid
    assert missing.valid
    assert any(
        item.severity == "warning" and item.field == "feature_csv_path"
        for item in missing.diagnostics
    )
    assert any(
        item.severity == "error"
        and "outside dataset_root" in item.message
        for item in traversal.diagnostics
    )
    assert any(
        item.severity == "error"
        and "outside dataset_root" in item.message
        for item in outside.diagnostics
    )


def test_symlink_escape_is_rejected_when_supported(tmp_path):
    outside = tmp_path.parent / "outside.csv"
    outside.write_text("frame_index\n0\n", encoding="utf-8")
    link = tmp_path / "features-link.csv"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("Symlinks are unavailable in this test environment")

    result = _validate(
        _row(feature_csv_path=link.name),
        options=ManifestValidationOptions(dataset_root=tmp_path),
    )

    assert any(
        item.severity == "error"
        and item.field == "feature_csv_path"
        and "outside dataset_root" in item.message
        for item in result.diagnostics
    )


def test_cli_exit_codes_for_valid_and_invalid_manifests(tmp_path, monkeypatch, capsys):
    manifest = tmp_path / "manifest.csv"
    with manifest.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=REQUIRED_COLUMNS)
        writer.writeheader()
        writer.writerow(_row())

    monkeypatch.setattr(sys, "argv", ["validate_annotation_manifest", str(manifest)])
    with pytest.raises(SystemExit) as valid_exit:
        main()
    assert valid_exit.value.code == 0
    capsys.readouterr()

    with manifest.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=REQUIRED_COLUMNS)
        writer.writeheader()
        writer.writerow(_row(movement_label="contact"))
    monkeypatch.setattr(sys, "argv", ["validate_annotation_manifest", str(manifest)])
    with pytest.raises(SystemExit) as invalid_exit:
        main()
    assert invalid_exit.value.code == 1
